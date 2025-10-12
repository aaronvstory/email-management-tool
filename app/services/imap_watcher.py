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
    account_id: int = None  # Database account ID for storing emails
    db_path: str = "email_manager.db"  # Path to database


class ImapWatcher:
    def __init__(self, cfg: AccountConfig):
        self.cfg = cfg
        self._client = None  # set in _connect
        self._last_hb = 0.0
        
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

    def _connect(self):
        try:
            log.info("Connecting to IMAP %s:%s (ssl=%s)", self.cfg.imap_host, self.cfg.imap_port, self.cfg.use_ssl)
            ssl_context = sslmod.create_default_context() if self.cfg.use_ssl else None
            # Apply connection timeout from env (EMAIL_CONN_TIMEOUT, clamp 5..60, default 15)
            try:
                to = int(os.getenv("EMAIL_CONN_TIMEOUT", "15"))
                to = max(5, min(60, to))
            except Exception:
                to = 15
            client = IMAPClient(
                self.cfg.imap_host,
                port=self.cfg.imap_port,
                ssl=self.cfg.use_ssl,
                ssl_context=ssl_context,
                timeout=to
            )
            client.login(self.cfg.username, self.cfg.password)
            log.info("Logged in as %s", self.cfg.username)
            capabilities = client.capabilities()
            log.debug("Server capabilities: %s", capabilities)
            # Ensure folders
            for folder in (self.cfg.inbox, self.cfg.quarantine):
                try:
                    client.select_folder(folder, readonly=False)
                except Exception:
                    try:
                        client.create_folder(folder)
                        log.info("Created folder %s", folder)
                    except Exception:
                        log.debug("Folder %s may already exist", folder)
            client.select_folder(self.cfg.inbox, readonly=False)
            return client
        except Exception as e:
            log.error(f"Failed to connect to IMAP for {self.cfg.username}: {e}")
            # Record failure and possibly trip circuit breaker with better taxonomy
            msg = str(e).lower()
            if ('auth' in msg or 'login' in msg):
                reason = 'auth_failed'
            elif ('ssl' in msg or 'tls' in msg):
                reason = 'tls_failed'
            elif 'timeout' in msg:
                reason = 'timeout'
            else:
                reason = 'error'
            self._record_failure(reason)
            return None

    def _supports_uid_move(self) -> bool:
        try:
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
        log.debug("Copying %s to %s", uids, self.cfg.quarantine)
        client.copy(uids, self.cfg.quarantine)
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
        log.debug("Purging from INBOX")
        client.add_flags(uids, [b"\\Deleted"])  # use silent variant not exposed; acceptable
        try:
            client.expunge()
        except Exception as e:
            log.warning("EXPUNGE failed: %s", e)

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
                                if payload:
                                    body_text = payload.decode('utf-8', errors='ignore')
                            elif part.get_content_type() == "text/html":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body_html = payload.decode('utf-8', errors='ignore')
                    else:
                        content = email_msg.get_payload(decode=True)
                        if content:
                            body_text = content.decode('utf-8', errors='ignore')

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
            cur.execute(
                "INSERT OR REPLACE INTO worker_heartbeats(worker_id, last_heartbeat, status, error_count) VALUES(?, datetime('now'), ?, COALESCE((SELECT error_count FROM worker_heartbeats WHERE worker_id=?), 0))",
                (wid, status, wid),
            )
            conn.commit(); conn.close()
        except Exception:
            pass

    def _handle_new_messages(self, client, changed):
        # changed example: {b'EXISTS': 12}
        try:
            # Fetch new UIDs quickly: search for messages without a custom marker
            # Simpler: use 'RECENT' or last UID state; here we just fetch last N
            uids = client.search('UNSEEN')
        except Exception:
            uids = []
        if not uids:
            return
        log.info("Intercepting %d messages", len(uids))

        # Store in database before moving
        self._store_in_database(client, uids)

        # Then move to quarantine
        if self._supports_uid_move():
            self._move(uids)
        else:
            self._copy_purge(uids)

    @backoff.on_exception(backoff.expo, (socket.error, OSError, Exception), max_time=60 * 60)
    def run_forever(self):
        # Early stop if account disabled
        if self._should_stop():
            try:
                self._update_heartbeat("stopped")
            except Exception:
                pass
            return
        self._client = self._connect()
        client = self._client

        # Check if connection failed
        if not client:
            log.error("Failed to establish IMAP connection")
            time.sleep(10)  # Wait before retry
            return  # Let backoff handle retry

        last_idle_break = time.time()
        # Track UIDNEXT to reduce duplicate scans
        try:
            status = client.folder_status(self.cfg.inbox, [b'UIDNEXT'])
            last_uidnext = int(status.get(b'UIDNEXT') or 1)
        except Exception:
            last_uidnext = 1
        # initial heartbeat
        self._update_heartbeat("active"); self._last_hb = time.time()
        while True:
            # Stop if account was deactivated while running
            if self._should_stop():
                try:
                    self._update_heartbeat("stopped")
                except Exception:
                    pass
                try:
                    if client:
                        client.logout()
                except Exception:
                    pass
                return
            # Ensure client is still connected
            if not client:
                log.error("IMAP client disconnected, attempting reconnect")
                self._client = self._connect()
                client = self._client
                if not client:
                    time.sleep(10)
                    continue

            # Check IDLE support
            try:
                can_idle = b"IDLE" in (client.capabilities() or [])
            except Exception:
                can_idle = False
            if not can_idle:
                # Poll fallback every few seconds
                time.sleep(5)
                client.select_folder(self.cfg.inbox, readonly=False)
                self._handle_new_messages(client, {})
                if time.time() - self._last_hb > 30:
                    self._update_heartbeat("active"); self._last_hb = time.time()
                continue

            # Double-check client before IDLE
            if not client:
                log.error("Client lost before IDLE, restarting")
                break

            # Final check - client must not be None for context manager
            if client is None:
                log.error("Client is None before IDLE, restarting")
                break

            try:
                # Some imapclient versions do not return a context manager from idle(); use explicit start/stop
                client.idle()
                log.debug("Entered IDLE")
                start = time.time()
                while True:
                    responses = client.idle_check(timeout=30)
                    # Break and process on EXISTS/RECENT
                    changed = {k: v for (k, v) in responses} if responses else {}
                    if responses:
                        self._handle_new_messages(client, changed)
                    # periodic heartbeat
                    if time.time() - self._last_hb > 30:
                        self._update_heartbeat("active"); self._last_hb = time.time()
                    # Check stop request periodically during IDLE
                    if self._should_stop():
                        try:
                            client.idle_done()
                        except Exception:
                            pass
                        try:
                            client.logout()
                        except Exception:
                            pass
                        try:
                            self._update_heartbeat("stopped")
                        except Exception:
                            pass
                        return
                    # Keep alive / break idle periodically
                    now = time.time()
                    if (now - start) > self.cfg.idle_timeout or (now - last_idle_break) > self.cfg.idle_ping_interval:
                        try:
                            client.idle_done()
                        except Exception:
                            pass
                        client.noop()
                        # Opportunistic poll using UIDNEXT delta when possible
                        try:
                            client.select_folder(self.cfg.inbox, readonly=False)
                            try:
                                st2 = client.folder_status(self.cfg.inbox, [b'UIDNEXT'])
                                uidnext2 = int(st2.get(b'UIDNEXT') or last_uidnext)
                            except Exception:
                                uidnext2 = last_uidnext
                            new_uids = []
                            if uidnext2 > last_uidnext:
                                try:
                                    rng = f"UID {last_uidnext}:{uidnext2-1}"
                                    new_uids = client.search(rng)
                                except Exception:
                                    new_uids = []
                            # Fallback to UNSEEN if no range detected
                            if not new_uids:
                                try:
                                    new_uids = client.search('UNSEEN')
                                except Exception:
                                    new_uids = []
                            if new_uids:
                                # Persist and move
                                self._store_in_database(client, new_uids)
                                if self._supports_uid_move():
                                    self._move(new_uids)
                                else:
                                    self._copy_purge(new_uids)
                            last_uidnext = uidnext2
                        except Exception:
                            pass
                        last_idle_break = now
                        break
            except Exception as e:
                log.error(f"IDLE failed: {e}, reconnecting...")
                self._client = None
                break  # Exit inner loop to reconnect

    def close(self):
        try:
            if self._client:
                self._client.logout()
        finally:
            self._client = None


__all__ = ["AccountConfig", "ImapWatcher"]
import time
import threading
from typing import List

try:
    from imapclient import IMAPClient, exceptions as imap_exc
except Exception as e:  # pragma: no cover - import-time fallback
    IMAPClient = None  # type: ignore
    imap_exc = None  # type: ignore


class IMAPRapidInterceptor(threading.Thread):
    daemon = True

    def __init__(self, imap_host: str, username: str, password: str, quarantine_folder: str = "Quarantine"):
        super().__init__(name=f"imap-rapid-{username}")
        self.imap_host = imap_host
        self.username = username
        self.password = password
        self.quarantine = quarantine_folder
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _connect(self):
        if IMAPClient is None:
            raise RuntimeError("imapclient is not installed")
        c = IMAPClient(self.imap_host, ssl=True)
        c.login(self.username, self.password)
        # Ensure Quarantine exists
        try:
            c.select_folder(self.quarantine)
        except Exception:
            c.create_folder(self.quarantine)
        return c

    def _move_atomic(self, c, uids: List[int]):
        try:
            # UID MOVE if supported
            c.move(uids, self.quarantine)
        except Exception:
            # Fallback: COPY + DELETE + EXPUNGE
            c.copy(uids, self.quarantine)
            c.add_flags(uids, [b'\\Deleted'])
            c.expunge()

    def run(self):
        while not self._stop.is_set():
            c = None
            try:
                c = self._connect()
                c.select_folder("INBOX")
                status = c.folder_status("INBOX", [b'UIDNEXT'])
                last_uidnext = status[b'UIDNEXT']
                while not self._stop.is_set():
                    # IDLE wait
                    with c.idle():
                        _ = c.idle_check(timeout=60)
                    # On exit from IDLE, check for new messages
                    status2 = c.folder_status("INBOX", [b'UIDNEXT'])
                    uidnext2 = status2[b'UIDNEXT']
                    if uidnext2 > last_uidnext:
                        new_uid_first = last_uidnext
                        new_uids = c.search(f'UID {new_uid_first}:{uidnext2 - 1}')
                        if new_uids:
                            self._move_atomic(c, new_uids)
                        last_uidnext = uidnext2
            except Exception:
                time.sleep(2.0)
            finally:
                if c:
                    try:
                        c.logout()
                    except Exception:
                        pass
