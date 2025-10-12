"""
IMAP watcher implementing rapid copy+purge interception.

Contract:
- Input: account settings: host, port, username, password, ssl, folders
- Behavior: maintain an IDLE loop on INBOX; on new message UIDs, immediately copy to Quarantine, then delete from INBOX
- Fallback: if UID MOVE supported, prefer it over copy+purge
- Reliability: auto-reconnect with exponential backoff

This module is intentionally decoupled from Flask; it can be used by a runner script.
"""
from __future__ import annotations

import logging
import os
import socket
import ssl as sslmod
import time
from dataclasses import dataclass
import sqlite3
import json
from datetime import datetime
from email import message_from_bytes, policy
from typing import Optional

import backoff
from imapclient import IMAPClient


log = logging.getLogger(__name__)


@dataclass
class AccountConfig:
    imap_host: str
    imap_port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    inbox: str = "INBOX"
    quarantine: str = "Quarantine"
    idle_timeout: int = 25 * 60  # 25 minutes typical server limit < 30m
    idle_ping_interval: int = 14 * 60  # break idle to keep alive
    mark_seen_quarantine: bool = True
    account_id: Optional[int] = None  # Database account ID for storing emails
    db_path: str = "email_manager.db"  # Path to database


class ImapWatcher:
    def __init__(self, cfg: AccountConfig):
        self.cfg = cfg
        self._client: Optional[IMAPClient] = None  # set in _connect
        self._last_hb = 0.0
        self._last_uidnext = 1

    def _should_stop(self) -> bool:
        """Return True if the account is deactivated in DB (is_active=0)."""
        try:
            if not self.cfg.account_id:
                return False
            conn = sqlite3.connect(self.cfg.db_path)
            cur = conn.cursor()
            row = cur.execute("SELECT is_active FROM email_accounts WHERE id=?", (self.cfg.account_id,)).fetchone()
            conn.close()
            if not row:
                return True
            is_active = int(row[0]) if row[0] is not None else 0
            return is_active == 0
        except Exception:
            # On DB error, do not force stop
            return False

    def _record_failure(self, reason: str = "error"):
        """Increment failure counter and open circuit if threshold exceeded."""
        try:
            if not self.cfg.account_id:
                return
            conn = sqlite3.connect(self.cfg.db_path)
            cur = conn.cursor()
            # Ensure heartbeats table has error_count column
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    worker_id TEXT PRIMARY KEY,
                    last_heartbeat TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    error_count INTEGER DEFAULT 0
                )
                """
            )
            # Backfill column if table existed without error_count
            try:
                cols = [r[1] for r in cur.execute("PRAGMA table_info(worker_heartbeats)").fetchall()]
                if 'error_count' not in cols:
                    cur.execute("ALTER TABLE worker_heartbeats ADD COLUMN error_count INTEGER DEFAULT 0")
            except Exception:
                pass
            wid = f"imap_{self.cfg.account_id}"
            # Upsert and increment error_count
            cur.execute(
                """
                INSERT INTO worker_heartbeats(worker_id, last_heartbeat, status, error_count)
                VALUES(?, datetime('now'), ?, 1)
                ON CONFLICT(worker_id) DO UPDATE SET
                  last_heartbeat = excluded.last_heartbeat,
                  status = excluded.status,
                  error_count = COALESCE(worker_heartbeats.error_count, 0) + 1
                """,
                (wid, reason),
            )
            # Check threshold
            row = cur.execute("SELECT error_count FROM worker_heartbeats WHERE worker_id=?", (wid,)).fetchone()
            count = int(row[0]) if row and row[0] is not None else 0
            if count >= int(os.getenv('IMAP_CIRCUIT_THRESHOLD', '5')):
                # Open circuit: disable account to stop retry loop
                cur.execute(
                    "UPDATE email_accounts SET is_active=0, last_error=? WHERE id=?",
                    (f"circuit_open:{reason}", self.cfg.account_id),
                )
            conn.commit(); conn.close()
        except Exception:
            pass

    def _connect(self) -> Optional[IMAPClient]:
        """Establish IMAP connection with validation and error handling.

        Returns:
            IMAPClient instance on success, None on failure
        """
        try:
            # Validate credentials before attempting connection
            if not self.cfg.username or not self.cfg.password:
                log.error("Missing credentials for account %s - username or password is empty", self.cfg.account_id)
                self._record_failure('missing_credentials')
                return None

            if not self.cfg.imap_host:
                log.error("Missing IMAP host for account %s", self.cfg.account_id)
                self._record_failure('missing_config')
                return None

            log.info("Connecting to IMAP %s:%s (ssl=%s) for account %s",
                     self.cfg.imap_host, self.cfg.imap_port, self.cfg.use_ssl, self.cfg.account_id)

            ssl_context = sslmod.create_default_context() if self.cfg.use_ssl else None

            # Apply connection timeout from env (EMAIL_CONN_TIMEOUT, clamp 5..60, default 15)
            try:
                to = int(os.getenv("EMAIL_CONN_TIMEOUT", "15"))
                to = max(5, min(60, to))
            except Exception:
                to = 15

            # Create IMAP client with timeout
            client = IMAPClient(
                self.cfg.imap_host,
                port=self.cfg.imap_port,
                ssl=self.cfg.use_ssl,
                ssl_context=ssl_context,
                timeout=to
            )

            # Attempt login with masked password in logs
            log.debug("Attempting login as %s", self.cfg.username)
            client.login(self.cfg.username, self.cfg.password)
            log.info("Successfully logged in as %s for account %s", self.cfg.username, self.cfg.account_id)

            capabilities = client.capabilities()
            log.debug("Server capabilities for account %s: %s", self.cfg.account_id, capabilities)
            # Ensure folders (robust: try Quarantine variants with server delimiter)
            # Always ensure INBOX first
            try:
                client.select_folder(self.cfg.inbox, readonly=False)
            except Exception:
                # Some servers require upper-case name
                client.select_folder("INBOX", readonly=False)

            # Resolve folder delimiter and build robust candidate list
            delim = None
            try:
                folders = client.list_folders()
                # folders items: (flags, delimiter, name)
                if folders and len(folders[0]) >= 2:
                    delim = folders[0][1]
                    if isinstance(delim, bytes):
                        try:
                            delim = delim.decode('utf-8', errors='ignore')
                        except Exception:
                            pass
            except Exception:
                delim = None

            # Try to ensure quarantine folder with several candidates (ordered by preference)
            pref = str(os.getenv('IMAP_QUARANTINE_PREFERENCE', 'auto')).lower()
            base_name = self.cfg.quarantine
            inbox_slash = f"INBOX/{base_name}"
            inbox_dot = f"INBOX.{base_name}"
            if pref == 'inbox':
                q_candidates = [inbox_slash, inbox_dot, base_name]
            elif pref == 'plain':
                q_candidates = [base_name, inbox_slash, inbox_dot]
            else:
                q_candidates = [base_name, inbox_slash, inbox_dot]
            # If we detected a delimiter we trust, add that specific variant too
            try:
                if delim in ("/", "."):
                    q_candidates.append(f"INBOX{delim}{self.cfg.quarantine}")
            except Exception:
                pass

            ensured = False
            for qname in q_candidates:
                try:
                    client.select_folder(qname, readonly=False)
                    self.cfg.quarantine = qname
                    ensured = True
                    if str(os.getenv('IMAP_LOG_VERBOSE','0')).lower() in ('1','true','yes'):
                        log.info("Using quarantine folder: %s", qname)
                    break
                except Exception:
                    try:
                        client.create_folder(qname)
                        client.select_folder(qname, readonly=False)
                        self.cfg.quarantine = qname
                        ensured = True
                        log.info("Created folder %s", qname)
                        break
                    except Exception:
                        log.debug("Folder %s not available yet", qname)
                        continue

            # Fall back to original inbox if quarantine couldn't be ensured (should be rare)
            try:
                client.select_folder(self.cfg.inbox, readonly=False)
            except Exception:
                client.select_folder("INBOX", readonly=False)
            # If we still didn't ensure quarantine, default to INBOX.Quarantine for safety
            if not ensured:
                try:
                    self.cfg.quarantine = "INBOX.Quarantine"
                except Exception:
                    pass
            # Initialize UIDNEXT tracking for fast delta scans
            try:
                status = client.folder_status(self.cfg.inbox, [b'UIDNEXT'])
                self._last_uidnext = int(status.get(b'UIDNEXT') or 1)
            except Exception:
                self._last_uidnext = 1
            return client
        except Exception as e:
            # Detailed error logging with classification
            error_msg = str(e)
            error_lower = error_msg.lower()

            # Classify error type for circuit breaker
            if 'authenticationfailed' in error_lower or 'auth' in error_lower or 'login' in error_lower:
                reason = 'auth_failed'
                log.error("IMAP authentication failed for account %s (%s): %s - Check credentials in database",
                         self.cfg.account_id, self.cfg.username, error_msg)
                log.error("Hint: For Gmail/Outlook, use App Passwords. For Hostinger, use regular password.")
            elif 'ssl' in error_lower or 'tls' in error_lower or 'certificate' in error_lower:
                reason = 'tls_failed'
                log.error("IMAP SSL/TLS error for account %s (%s): %s - Check SSL settings and port",
                         self.cfg.account_id, self.cfg.username, error_msg)
            elif 'timeout' in error_lower or 'timed out' in error_lower:
                reason = 'timeout'
                log.error("IMAP connection timeout for account %s (%s:%s): %s - Check network/firewall",
                         self.cfg.account_id, self.cfg.imap_host, self.cfg.imap_port, error_msg)
            elif 'refused' in error_lower or 'unreachable' in error_lower:
                reason = 'connection_refused'
                log.error("IMAP connection refused for account %s (%s:%s): %s - Check host/port settings",
                         self.cfg.account_id, self.cfg.imap_host, self.cfg.imap_port, error_msg)
            else:
                reason = 'error'
                log.error("IMAP connection error for account %s (%s): %s",
                         self.cfg.account_id, self.cfg.username, error_msg)

            # Record failure for circuit breaker
            self._record_failure(reason)

            # Update database with error details if account_id exists
            try:
                if self.cfg.account_id:
                    conn = sqlite3.connect(self.cfg.db_path)
                    cur = conn.cursor()
                    # Truncate error message to reasonable length
                    truncated_error = error_msg[:500] if len(error_msg) > 500 else error_msg
                    cur.execute(
                        "UPDATE email_accounts SET last_error=?, last_checked=datetime('now') WHERE id=?",
                        (f"{reason}: {truncated_error}", self.cfg.account_id)
                    )
                    conn.commit()
                    conn.close()
            except Exception as db_error:
                log.warning("Could not update error status in database: %s", db_error)

            return None

    def _supports_uid_move(self) -> bool:
        # Allow forcing COPY+DELETE+EXPUNGE via env for servers with MOVE quirks
        try:
            if str(os.getenv('IMAP_FORCE_COPY_PURGE', '0')).lower() in ('1','true','yes'):
                return False
            caps = set(self._client.capabilities()) if self._client else set()
            return b"UIDPLUS" in caps or b"MOVE" in caps
        except Exception:
            return False

    def _copy_purge(self, uids):
        """Copy to quarantine then purge from INBOX quickly to minimize traces."""
        if not uids:
            return
        client = self._client
        if client is None:
            return
        if str(os.getenv('IMAP_LOG_VERBOSE','0')).lower() in ('1','true','yes'):
            log.info("Copying %s to %s", uids, self.cfg.quarantine)
        else:
            log.debug("Copying %s to %s", uids, self.cfg.quarantine)
        # Attempt copy, retrying with alternate folder names on namespace errors
        copy_ok = False
        last_err = None
        alt_targets = [self.cfg.quarantine]
        # Add common INBOX-prefixed variants
        if self.cfg.quarantine not in (f"INBOX/{self.cfg.quarantine}", f"INBOX.{self.cfg.quarantine}"):
            alt_targets.extend([f"INBOX/{self.cfg.quarantine}", f"INBOX.{self.cfg.quarantine}"])
        # Also explicit defaults
        alt_targets.extend(["INBOX/Quarantine", "INBOX.Quarantine", "Quarantine"])  # ensure a few options
        tried = set()
        for tgt in alt_targets:
            if tgt in tried:
                continue
            tried.add(tgt)
            try:
                # Ensure target exists, try create if needed
                try:
                    client.select_folder(tgt, readonly=False)
                except Exception:
                    try:
                        client.create_folder(tgt)
                    except Exception:
                        pass
                # Reselect INBOX (source) to ensure UIDs refer to current mailbox
                try:
                    client.select_folder(self.cfg.inbox, readonly=False)
                except Exception:
                    client.select_folder("INBOX", readonly=False)
                client.copy(uids, tgt)
                # Success: pin quarantine to working target
                self.cfg.quarantine = tgt
                copy_ok = True
                break
            except Exception as e:
                last_err = e
                log.debug("Copy to %s failed: %s", tgt, e)
                continue
        if not copy_ok:
            # Surface a concise error but do not crash the loop
            log.error("All COPY attempts failed for UIDs %s: %s", uids, last_err)
            return
        # Mark seen in quarantine optionally to reduce badge noise
        if self.cfg.mark_seen_quarantine:
            try:
                client.select_folder(self.cfg.quarantine, readonly=False)
                client.add_flags(uids, [b"\\Seen"])  # same UIDs valid in target on many servers with UIDPLUS
            except Exception:
                # If UIDs differ post-copy, ignore silently; not critical
                log.debug("Could not set Seen in quarantine; continuing")
            finally:
                client.select_folder(self.cfg.inbox, readonly=False)
        if str(os.getenv('IMAP_LOG_VERBOSE','0')).lower() in ('1','true','yes'):
            log.info("Purging from INBOX")
        else:
            log.debug("Purging from INBOX")
        # Ensure we're operating on INBOX
        try:
            client.select_folder(self.cfg.inbox, readonly=False)
        except Exception:
            pass
        # Mark \Deleted using UID semantics (IMAPClient uses UIDs by default)
        try:
            client.add_flags(uids, [b"\\Deleted"])  # mark for deletion
        except Exception as e:
            log.warning("Adding \\Deleted flag failed: %s", e)

        # Try standard EXPUNGE first
        expunged = False
        try:
            client.expunge()
            expunged = True
        except Exception as e:
            log.warning("EXPUNGE failed: %s", e)
        # If server supports UIDPLUS, try UID EXPUNGE for the specific UIDs
        if not expunged:
            try:
                caps = set(client.capabilities() or [])
                if b"UIDPLUS" in caps and hasattr(client, "uid_expunge"):
                    client.uid_expunge(uids)
                    expunged = True
            except Exception as e:
                log.warning("UID EXPUNGE failed: %s", e)
        # Final fallback: delete_messages helper then expunge
        if not expunged:
            try:
                if hasattr(client, "delete_messages"):
                    client.delete_messages(uids, silent=False)
                client.expunge()
                expunged = True
            except Exception as e:
                log.error("Failed to purge deleted messages: %s", e)

    def _move(self, uids):
        client = self._client
        if client is None or not uids:
            return
        try:
            client.move(uids, self.cfg.quarantine)
        except Exception as e:
            log.debug("MOVE failed (%s); fallback copy+purge", e)
            self._copy_purge(uids)

    def _store_in_database(self, client, uids):
        """Store intercepted emails in database with account_id (idempotent).

        - Fetch RFC822 + metadata (ENVELOPE, FLAGS, INTERNALDATE)
        - Skip insert if a row with same Message-ID already exists
        - Persist original_uid, original_internaldate, original_message_id
        """
        if not self.cfg.account_id or not uids:
            return

        try:
            # Fetch email data before moving (include INTERNALDATE for server timestamp)
            fetch_data = client.fetch(uids, ['RFC822', 'ENVELOPE', 'FLAGS', 'INTERNALDATE'])

            conn = sqlite3.connect(self.cfg.db_path)
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row

            for uid, data in fetch_data.items():
                try:
                    # Parse email
                    raw_email = data[b'RFC822']
                    email_msg = message_from_bytes(raw_email, policy=policy.default)

                    # Extract envelope data
                    envelope = data.get(b'ENVELOPE', {})

                    # Extract basic fields
                    sender = str(email_msg.get('From', ''))
                    recipients = json.dumps([str(email_msg.get('To', ''))])
                    subject = str(email_msg.get('Subject', 'No Subject'))
                    original_msg_id = (email_msg.get('Message-ID') or '').strip() or None
                    # Use header Message-ID when available; otherwise stable fallback
                    message_id = original_msg_id or f"imap_{uid}_{datetime.now().timestamp()}"

                    # Extract body
                    body_text = ""
                    body_html = ""
                    if email_msg.is_multipart():
                        for part in email_msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    body_text = payload.decode('utf-8', errors='ignore')
                                elif isinstance(payload, str):
                                    body_text = payload
                            elif part.get_content_type() == "text/html":
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    body_html = payload.decode('utf-8', errors='ignore')
                                elif isinstance(payload, str):
                                    body_html = payload
                    else:
                        content = email_msg.get_payload(decode=True)
                        if isinstance(content, bytes):
                            body_text = content.decode('utf-8', errors='ignore')
                        elif isinstance(content, str):
                            body_text = content

                    # Idempotency: skip if Message-ID already stored
                    try:
                        if original_msg_id:
                            row = cursor.execute("SELECT id FROM email_messages WHERE message_id=?", (original_msg_id,)).fetchone()
                            if row:
                                log.debug("Skipping duplicate message_id=%s (uid=%s)", original_msg_id, uid)
                                continue
                    except Exception:
                        pass

                    # Derive INTERNALDATE
                    internal_dt = None
                    try:
                        internal_obj = data.get(b'INTERNALDATE')
                        if internal_obj:
                            if isinstance(internal_obj, datetime):
                                internal_dt = internal_obj.isoformat()
                            else:
                                # Fallback: best-effort string cast
                                internal_dt = str(internal_obj)
                    except Exception:
                        internal_dt = None

                    # Store in database with account_id
                    cursor.execute('''
                        INSERT INTO email_messages
                        (message_id, sender, recipients, subject, body_text, body_html,
                         raw_content, account_id, interception_status, direction,
                         original_uid, original_internaldate, original_message_id,
                         created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ''', (
                        message_id,
                        sender,
                        recipients,
                        subject,
                        body_text,
                        body_html,
                        raw_email,
                        self.cfg.account_id,
                        'HELD',
                        'inbound',
                        int(uid),
                        internal_dt,
                        original_msg_id
                    ))

                    log.info(f"Stored email {subject} from {sender} for account {self.cfg.account_id}")

                except Exception as e:
                    log.error(f"Failed to store email UID {uid}: {e}")

            conn.commit()
            conn.close()

        except Exception as e:
            log.error(f"Failed to store emails in database: {e}")

    def _update_heartbeat(self, status: str = "active"):
        """Best-effort upsert of a heartbeat record for /healthz."""
        try:
            if not self.cfg.account_id:
                return
            conn = sqlite3.connect(self.cfg.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    worker_id TEXT PRIMARY KEY,
                    last_heartbeat TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    error_count INTEGER DEFAULT 0
                )
                """
            )
            # Backfill column if missing
            try:
                cols = [r[1] for r in cur.execute("PRAGMA table_info(worker_heartbeats)").fetchall()]
                if 'error_count' not in cols:
                    cur.execute("ALTER TABLE worker_heartbeats ADD COLUMN error_count INTEGER DEFAULT 0")
            except Exception:
                pass
            wid = f"imap_{self.cfg.account_id}"
            # Reset error_count to 0 on healthy heartbeat; otherwise preserve
            cur.execute(
                """
                INSERT INTO worker_heartbeats(worker_id, last_heartbeat, status, error_count)
                VALUES(?, datetime('now'), ?, CASE WHEN ?='active' THEN 0 ELSE 0 END)
                ON CONFLICT(worker_id) DO UPDATE SET
                  last_heartbeat = excluded.last_heartbeat,
                  status = excluded.status,
                  error_count = CASE WHEN excluded.status='active' THEN 0 ELSE COALESCE(worker_heartbeats.error_count, 0) END
                """,
                (wid, status, status),
            )
            conn.commit(); conn.close()
        except Exception:
            pass

    def _handle_new_messages(self, client, changed):
        # changed example: {b'EXISTS': 12}
        # Build a robust candidate set using UIDNEXT deltas + last-N sweep, then filter out already-processed UIDs
        candidates: list[int] = []
        try:
            client.select_folder(self.cfg.inbox, readonly=False)
            # 1) UIDNEXT delta
            try:
                st = client.folder_status(self.cfg.inbox, [b'UIDNEXT'])
                uidnext_now = int(st.get(b'UIDNEXT') or self._last_uidnext)
            except Exception:
                uidnext_now = self._last_uidnext
            if uidnext_now > self._last_uidnext:
                try:
                    all_uids = client.search('ALL')
                    delta = [int(u) for u in all_uids if self._last_uidnext <= int(u) < uidnext_now]
                    candidates.extend(delta)
                except Exception:
                    pass
            # 2) Last-N sweep to catch provider quirks (e.g., flags set early)
            try:
                sweep_n = 50
                try:
                    sweep_n = max(10, min(500, int(os.getenv('IMAP_SWEEP_LAST_N', '50'))))
                except Exception:
                    sweep_n = 50
                all_uids2 = client.search('ALL')
                recent = sorted([int(u) for u in all_uids2])[-sweep_n:]
                candidates.extend(recent)
            except Exception:
                pass
        except Exception:
            pass

        # De-dup candidates
        if not candidates:
            return
        uniq = sorted(set(candidates))

        # Filter out UIDs we've already stored for this account
        try:
            conn = sqlite3.connect(self.cfg.db_path)
            cur = conn.cursor()
            placeholders = ",".join(["?"] * len(uniq))
            params = [self.cfg.account_id] + uniq
            seen = set()
            try:
                rows = cur.execute(
                    f"SELECT original_uid FROM email_messages WHERE account_id=? AND original_uid IN ({placeholders})",
                    params,
                ).fetchall()
                seen = {int(r[0]) for r in rows if r and r[0] is not None}
            except Exception:
                seen = set()
            finally:
                conn.close()
            to_process = [u for u in uniq if u not in seen]
        except Exception:
            to_process = uniq

        if not to_process:
            # Advance tracker to latest observed window
            try:
                self._last_uidnext = max(self._last_uidnext, max(uniq) + 1)
            except Exception:
                pass
            return

        log.info("Intercepting %d messages (acct=%s): %s", len(to_process), self.cfg.account_id, to_process)

        # Store in database before moving
        self._store_in_database(client, to_process)

        # Then move to quarantine
        if self._supports_uid_move():
            try:
                self._move(to_process)
                log.info("Moved %d messages to %s (acct=%s)", len(to_process), self.cfg.quarantine, self.cfg.account_id)
            except Exception as e:
                log.warning("MOVE failed, falling back to copy+purge: %s", e)
                self._copy_purge(to_process)
                log.info("Copied+purged %d messages to %s (acct=%s)", len(to_process), self.cfg.quarantine, self.cfg.account_id)
        else:
            self._copy_purge(to_process)
            log.info("Copied+purged %d messages to %s (acct=%s)", len(to_process), self.cfg.quarantine, self.cfg.account_id)

        # Advance tracker past the highest processed UID
        try:
            self._last_uidnext = max(self._last_uidnext, max(to_process) + 1)
        except Exception:
            pass

    @backoff.on_exception(backoff.expo, (socket.error, OSError, Exception), max_time=60 * 60)
    def run_forever(self):
        """Main IMAP monitoring loop with robust error handling and reconnection logic."""
        # Early stop if account disabled
        if self._should_stop():
            try:
                self._update_heartbeat("stopped")
            except Exception:
                pass
            log.info("Account %s is disabled, stopping watcher", self.cfg.account_id)
            return

        # Attempt connection with validation
        self._client = self._connect()
        if self._client is None:
            log.error("Failed to establish IMAP connection for account %s", self.cfg.account_id)
            self._update_heartbeat("auth_failed")
            time.sleep(10)  # Wait before backoff retry
            raise ConnectionError("IMAP connection failed - authentication or network issue")

        client = self._client
        log.info("IMAP watcher started successfully for account %s (%s)", self.cfg.account_id, self.cfg.username)

        last_idle_break = time.time()
        # Track UIDNEXT to reduce duplicate scans
        try:
            status = client.folder_status(self.cfg.inbox, [b'UIDNEXT'])
            self._last_uidnext = int(status.get(b'UIDNEXT') or 1)
        except Exception as e:
            log.warning("Could not fetch UIDNEXT: %s", e)
            self._last_uidnext = 1

        # initial heartbeat
        self._update_heartbeat("active")
        self._last_hb = time.time()

        while True:
            # Stop if account was deactivated while running
            if self._should_stop():
                log.info("Account %s deactivated, stopping watcher", self.cfg.account_id)
                try:
                    self._update_heartbeat("stopped")
                except Exception:
                    pass
                try:
                    if self._client:
                        self._client.logout()
                except Exception:
                    pass
                return

            # Validate client connection before use
            if self._client is None or client is None:
                log.warning("Client connection lost for account %s, attempting reconnect", self.cfg.account_id)
                self._client = self._connect()
                client = self._client
                if self._client is None:
                    log.error("Reconnection failed for account %s", self.cfg.account_id)
                    time.sleep(10)
                    continue
                log.info("Reconnected successfully for account %s", self.cfg.account_id)

            # Check IDLE support
            try:
                can_idle = b"IDLE" in (client.capabilities() or [])
            except Exception as e:
                log.warning("Could not check IDLE capability: %s", e)
                can_idle = False

            if not can_idle:
                # Poll fallback every few seconds for servers without IDLE
                try:
                    time.sleep(5)
                    client.select_folder(self.cfg.inbox, readonly=False)
                    self._handle_new_messages(client, {})
                    if time.time() - self._last_hb > 30:
                        self._update_heartbeat("active")
                        self._last_hb = time.time()
                except Exception as e:
                    log.error("Poll fallback failed: %s", e)
                    self._client = None
                    client = None
                continue

            # IDLE mode - explicit start/stop (not context manager)
            try:
                # Validate client one more time before IDLE
                if self._client is None or client is None:
                    log.error("Client is None before IDLE, restarting loop")
                    continue

                client.idle()
                log.debug("Entered IDLE mode for account %s", self.cfg.account_id)
                idle_start = time.time()

                while True:
                    # Validate client is still valid during IDLE
                    if self._client is None or client is None:
                        log.error("Client became None during IDLE, exiting IDLE loop")
                        break

                    responses = client.idle_check(timeout=30)
                    # Break and process on EXISTS/RECENT
                    changed = {k: v for (k, v) in responses} if responses else {}
                    if responses:
                        self._handle_new_messages(client, changed)

                    # periodic heartbeat
                    if time.time() - self._last_hb > 30:
                        self._update_heartbeat("active")
                        self._last_hb = time.time()

                    # Check stop request periodically during IDLE
                    if self._should_stop():
                        log.info("Stop requested during IDLE for account %s", self.cfg.account_id)
                        try:
                            client.idle_done()
                        except Exception:
                            pass
                        try:
                            if self._client:
                                self._client.logout()
                        except Exception:
                            pass
                        try:
                            self._update_heartbeat("stopped")
                        except Exception:
                            pass
                        return

                    # Keep alive / break idle periodically
                    now = time.time()
                    if (now - idle_start) > self.cfg.idle_timeout or (now - last_idle_break) > self.cfg.idle_ping_interval:
                        try:
                            client.idle_done()
                        except Exception as e:
                            log.warning("idle_done() failed: %s", e)

                        try:
                            client.noop()
                        except Exception as e:
                            log.warning("NOOP failed: %s", e)
                            # Connection likely lost
                            self._client = None
                            client = None
                            break

                        # Opportunistic poll using UIDNEXT delta when possible
                        try:
                            client.select_folder(self.cfg.inbox, readonly=False)
                            try:
                                st2 = client.folder_status(self.cfg.inbox, [b'UIDNEXT'])
                                uidnext2 = int(st2.get(b'UIDNEXT') or self._last_uidnext)
                            except Exception:
                                uidnext2 = self._last_uidnext
                            new_uids = []
                            if uidnext2 > self._last_uidnext:
                                try:
                                    all_uids2 = client.search('ALL')
                                    new_uids = [int(u) for u in all_uids2 if self._last_uidnext <= int(u) < uidnext2]
                                except Exception:
                                    new_uids = []
                            # Fallback to UNSEEN if no range detected
                            if not new_uids:
                                try:
                                    new_uids = [int(u) for u in client.search('UNSEEN')]
                                except Exception:
                                    new_uids = []
                            if new_uids:
                                # Persist and move
                                self._store_in_database(client, new_uids)
                                if self._supports_uid_move():
                                    self._move(new_uids)
                                else:
                                    self._copy_purge(new_uids)
                                # Advance tracker to just after the highest UID we processed
                                try:
                                    self._last_uidnext = max(self._last_uidnext, max(int(u) for u in new_uids) + 1)
                                except Exception:
                                    self._last_uidnext = uidnext2
                        except Exception as e:
                            log.warning("Poll during IDLE break failed: %s", e)

                        last_idle_break = now
                        break  # Exit inner IDLE loop to restart IDLE

            except Exception as e:
                log.error("IDLE loop failed for account %s: %s", self.cfg.account_id, e)
                try:
                    if self._client:
                        self._client.idle_done()
                except Exception:
                    pass
                self._client = None
                client = None
                time.sleep(5)  # Brief pause before reconnect
                # Loop continues, will reconnect at top

    def close(self):
        try:
            if self._client:
                self._client.logout()
        finally:
            self._client = None


__all__ = ["AccountConfig", "ImapWatcher"]
