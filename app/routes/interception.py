"""Interception & Inbox Blueprint (Phase 2 Migration).

Contains: healthz, interception dashboard APIs, inbox API, edit, release, discard.
Diff and attachment scrubbing supported.
"""
import logging
import os
import time
import statistics
from datetime import datetime, timezone
import sqlite3

from typing import Dict, Any, Optional, cast
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user
from email.parser import BytesParser
from email.policy import default as default_policy
from email.utils import make_msgid
import difflib
import imaplib, ssl

from app.utils.db import get_db, DB_PATH
from app.utils.crypto import decrypt_credential, encrypt_credential
from app.utils.imap_helpers import _imap_connect_account, _ensure_quarantine, _move_uid_to_quarantine
from app.utils.email_markers import RELEASE_BYPASS_HEADER, RELEASE_EMAIL_ID_HEADER
from app.services.audit import log_action
import socket
from app.extensions import csrf, limiter
from app.utils.rate_limit import get_rate_limit_config, simple_rate_limit

# Prometheus metrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from functools import wraps
import shutil
import threading
from contextlib import contextmanager


_RELEASE_RATE_LIMIT = get_rate_limit_config('release', default_requests=30)
_EDIT_RATE_LIMIT = get_rate_limit_config('edit', default_requests=30)
_RELEASE_LIMIT_STRING = str(_RELEASE_RATE_LIMIT['limit_string'])
_EDIT_LIMIT_STRING = str(_EDIT_RATE_LIMIT['limit_string'])


bp_interception = Blueprint('interception_bp', __name__)
log = logging.getLogger(__name__)

def _db():
    """Get database connection with Row factory"""
    return get_db()

WORKER_HEARTBEATS = {}
_HEALTH_CACHE: Dict[str, Any] = {'ts': 0.0, 'payload': None}

SMTP_HOST = os.environ.get('SMTP_PROXY_HOST', '127.0.0.1')
SMTP_PORT = int(os.environ.get('SMTP_PROXY_PORT', '8587'))


@bp_interception.route('/healthz')
@limiter.exempt
def healthz():
    """Health check endpoint with security configuration status (without exposing secrets)."""
    now = time.time()
    if _HEALTH_CACHE['payload'] and now - _HEALTH_CACHE['ts'] < 5:
        cached = dict(_HEALTH_CACHE['payload']); cached['cached'] = True
        return jsonify(cached), 200 if cached.get('ok') else 503
    info: Dict[str, Any] = {
        'ok': True,
        'db': None,
        'held_count': 0,
        'released_24h': 0,
        'median_latency_ms': None,
        'workers': [],
        'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
    }

    # Add security configuration status (without exposing secret values)
    try:
        from flask import current_app
        secret_key = current_app.config.get('SECRET_KEY', '')
        info['security'] = {
            'secret_key_configured': bool(secret_key and len(secret_key) >= 32),
            'secret_key_prefix': secret_key[:8] if secret_key else '',  # Only first 8 chars for verification
            'csrf_enabled': current_app.config.get('WTF_CSRF_ENABLED', False),
            'csrf_time_limit': current_app.config.get('WTF_CSRF_TIME_LIMIT'),
            'session_cookie_secure': current_app.config.get('SESSION_COOKIE_SECURE', False),
            'session_cookie_httponly': current_app.config.get('SESSION_COOKIE_HTTPONLY', True),
        }
    except Exception:
        info['security'] = {'status': 'unavailable'}

    # Add IMAP watcher configuration status
    try:
        import os
        idle_disabled = str(os.getenv('IMAP_DISABLE_IDLE', '0')).lower() in ('1', 'true', 'yes')
        poll_interval = int(os.getenv('IMAP_POLL_INTERVAL', '30'))
        info['imap_config'] = {
            'mode': 'polling' if idle_disabled else 'idle+polling',
            'idle_disabled': idle_disabled,
            'poll_interval_seconds': poll_interval,
            'verbose_logging': str(os.getenv('IMAP_LOG_VERBOSE', '0')).lower() in ('1', 'true', 'yes'),
            'circuit_threshold': int(os.getenv('IMAP_CIRCUIT_THRESHOLD', '5'))
        }
    except Exception:
        info['imap_config'] = {'status': 'unavailable'}

    try:
        conn = _db(); cur = conn.cursor()
        info['held_count'] = cur.execute("SELECT COUNT(*) FROM email_messages WHERE direction='inbound' AND interception_status='HELD'").fetchone()[0]
        info['released_24h'] = cur.execute("SELECT COUNT(*) FROM email_messages WHERE direction='inbound' AND interception_status='RELEASED' AND created_at >= datetime('now','-1 day')").fetchone()[0]
        lat_rows = cur.execute("SELECT latency_ms FROM email_messages WHERE latency_ms IS NOT NULL ORDER BY id DESC LIMIT 200").fetchall()
        latencies = [r['latency_ms'] for r in lat_rows if r['latency_ms'] is not None]
        if latencies:
            info['median_latency_ms'] = int(statistics.median(latencies))
        # Worker heartbeats from DB (last 2 minutes)
        try:
            rows = cur.execute(
                """
                SELECT worker_id, last_heartbeat, status
                FROM worker_heartbeats
                WHERE datetime(last_heartbeat) > datetime('now', '-2 minutes')
                ORDER BY last_heartbeat DESC
                """
            ).fetchall()
            info['workers'] = [dict(r) for r in rows]
        except Exception:
            info['workers'] = []
        conn.close(); info['db'] = 'ok'
    except Exception as e:
        info['ok'] = False; info['error'] = str(e)
    # SMTP status
    smtp_info = {'listening': False, 'last_selfcheck_ts': None, 'last_inbound_ts': None}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        err = s.connect_ex((SMTP_HOST, SMTP_PORT))
        s.close()
        smtp_info['listening'] = (err == 0)
    except Exception:
        smtp_info['listening'] = False
    try:
        conn2 = _db(); cur2 = conn2.cursor()
        try:
            row = cur2.execute("SELECT value FROM system_status WHERE key='smtp_last_selfcheck' LIMIT 1").fetchone()
            if row and row['value']:
                smtp_info['last_selfcheck_ts'] = row['value']
        except Exception:
            pass
        try:
            r2 = cur2.execute("SELECT MAX(created_at) AS ts FROM email_messages WHERE direction='inbound'").fetchone()
            smtp_info['last_inbound_ts'] = r2['ts'] if r2 and r2['ts'] else None
        except Exception:
            pass
        conn2.close()
    except Exception:
        pass
    info['smtp'] = smtp_info
    _HEALTH_CACHE['ts'] = now; _HEALTH_CACHE['payload'] = info
    log.debug("[interception::healthz] refreshed", extra={'ok': info.get('ok'), 'held_count': info.get('held_count'), 'workers': len(info.get('workers', []))})
    return jsonify(info), 200 if info.get('ok') else 503

@bp_interception.route('/api/smtp-health')
@limiter.exempt
def api_smtp_health():
    """Lightweight SMTP health endpoint."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        ok = (s.connect_ex((SMTP_HOST, SMTP_PORT)) == 0)
        s.close()
    except Exception:
        ok = False
    last_sc = None; last_in = None
    try:
        conn = _db(); cur = conn.cursor()
        try:
            row = cur.execute("SELECT value FROM system_status WHERE key='smtp_last_selfcheck' LIMIT 1").fetchone()
            if row and row['value']:
                last_sc = row['value']
        except Exception:
            pass
        try:
            r2 = cur.execute("SELECT MAX(created_at) AS ts FROM email_messages WHERE direction='inbound'").fetchone()
            last_in = r2['ts'] if r2 and r2['ts'] else None
        except Exception:
            pass
        conn.close()
    except Exception:
        pass
    return jsonify({'ok': ok, 'listening': ok, 'last_selfcheck_ts': last_sc, 'last_inbound_ts': last_in})

@bp_interception.route('/metrics')
@limiter.exempt
def metrics():
    """
    Prometheus metrics endpoint.

    Exposes all instrumented metrics in Prometheus format.
    Update gauge metrics with current system state before returning.
    """
    try:
        # Update gauge metrics with current system state
        from app.utils.metrics import update_held_count, update_pending_count
        conn = _db()
        cur = conn.cursor()

        # Update held count
        held_count = cur.execute(
            "SELECT COUNT(*) FROM email_messages WHERE interception_status='HELD'"
        ).fetchone()[0]
        update_held_count(held_count)

        # Update pending count
        pending_count = cur.execute(
            "SELECT COUNT(*) FROM email_messages WHERE status='PENDING'"
        ).fetchone()[0]
        update_pending_count(pending_count)

        conn.close()
    except Exception as e:
        log.warning(f"Failed to update gauge metrics: {e}")

    # Generate and return Prometheus metrics
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@bp_interception.route('/interception')
@login_required
def interception_dashboard():
    """Redirect to unified email management with HELD filter"""
    from flask import redirect
    return redirect('/emails-unified?status=HELD')

@bp_interception.route('/interception-legacy')
@login_required
def interception_dashboard_legacy():
    """Legacy interception dashboard - kept for reference"""
    return render_template('dashboard_interception.html')

@bp_interception.route('/api/interception/held')
@login_required
def api_interception_held():
    conn = _db(); cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, account_id, interception_status, original_uid, sender, recipients, subject, latency_ms, created_at
        FROM email_messages
        WHERE direction='inbound' AND interception_status='HELD'
        ORDER BY id DESC LIMIT 200
    """).fetchall()
    latencies = [r['latency_ms'] for r in rows if r['latency_ms'] is not None]
    median_latency = int(statistics.median(latencies)) if latencies else None
    released24 = cur.execute("""
        SELECT COUNT(*) FROM email_messages
        WHERE direction='inbound' AND interception_status='RELEASED' AND created_at >= datetime('now','-1 day')
    """).fetchone()[0]
    accounts_active = cur.execute("SELECT COUNT(DISTINCT account_id) FROM email_messages WHERE direction='inbound'").fetchone()[0]
    conn.close()
    # Fix timezone: SQLite datetime('now') returns UTC without 'Z', JavaScript needs 'Z' suffix
    messages = []
    for r in rows:
        msg = dict(r)
        if msg.get('created_at') and isinstance(msg['created_at'], str):
            if not msg['created_at'].endswith('Z') and 'T' not in msg['created_at']:
                msg['created_at'] = msg['created_at'].replace(' ', 'T') + 'Z'
        messages.append(msg)
    return jsonify({'messages':messages, 'stats':{'held':len(rows),'released24h':released24,'median_latency_ms':median_latency,'accounts_active':accounts_active}})

@bp_interception.route('/api/interception/held/<int:msg_id>')
@login_required
def api_interception_get(msg_id:int):
    include_diff = request.args.get('include_diff') == '1'
    conn = _db(); cur = conn.cursor()
    row = cur.execute("SELECT * FROM email_messages WHERE id=? AND direction='inbound'", (msg_id,)).fetchone()
    if not row:
        conn.close(); return jsonify({'error':'not found'}), 404
    data = dict(row)
    raw_path = data.get('raw_path'); snippet = None
    if raw_path and os.path.exists(raw_path):
        try:
            with open(raw_path,'rb') as f: emsg = BytesParser(policy=default_policy).parsebytes(f.read())
            text_part = None
            if emsg.is_multipart():
                for part in emsg.walk():
                    if part.get_content_type()=='text/plain':
                        text_part = part.get_content(); break
                if text_part is None:
                    for part in emsg.walk():
                        if part.get_content_type()=='text/html':
                            import re; text_part = re.sub('<[^>]+>',' ', part.get_content()); break
            else:
                if emsg.get_content_type()=='text/plain': text_part = emsg.get_content()
                elif emsg.get_content_type()=='text/html':
                    import re; text_part = re.sub('<[^>]+>',' ', emsg.get_content())
            if text_part:
                snippet = ' '.join(text_part.split())[:500]
        except Exception:
            snippet = None
    data['preview_snippet'] = snippet
    if include_diff and snippet is not None:
        try:
            current_body = (row['body_text'] or '').strip()
            if current_body and current_body != snippet:
                diff_lines = list(difflib.unified_diff(snippet.splitlines(), current_body.splitlines(), fromfile='original', tofile='edited', lineterm=''))
                data['body_diff'] = diff_lines[:500]
        except Exception:
            data['body_diff'] = None
    conn.close(); return jsonify(data)

@bp_interception.route('/api/interception/release/<int:msg_id>', methods=['POST'])
@csrf.exempt
@limiter.limit(_RELEASE_LIMIT_STRING)
@simple_rate_limit('release', config=_RELEASE_RATE_LIMIT)
@login_required
def api_interception_release(msg_id:int):
    payload = request.get_json(silent=True) or {}
    edited_subject = payload.get('edited_subject'); edited_body = payload.get('edited_body')
    target_folder = payload.get('target_folder','INBOX')
    strip_attachments = bool(payload.get('strip_attachments'))
    conn = _db(); cur = conn.cursor()
    log.debug("[interception::release] begin", extra={'email_id': msg_id, 'target': target_folder})
    # Fetch regardless of current interception_status to support idempotency
    row = cur.execute("""
        SELECT em.*, ea.imap_host, ea.imap_port, ea.imap_username, ea.imap_password, ea.imap_use_ssl
        FROM email_messages em JOIN email_accounts ea ON em.account_id = ea.id
        WHERE em.id=? AND em.direction='inbound'
    """, (msg_id,)).fetchone()
    if not row:
        conn.close(); return jsonify({'ok':False,'reason':'not-found'}), 404
    interception_status = str((row['interception_status'] or '')).upper()
    # Idempotent success if already released
    if interception_status == 'RELEASED':
        conn.close(); return jsonify({'ok': True, 'reason': 'already-released'})
    # Discarded items cannot be released via this endpoint
    if interception_status == 'DISCARDED':
        conn.close(); return jsonify({'ok': False, 'reason': 'discarded'}), 409
    # Require HELD for a release action
    if interception_status != 'HELD':
        conn.close(); return jsonify({'ok': False, 'reason': 'not-held'}), 409

    # Default to persisted edits when payload doesn't include them
    if edited_subject is None:
        edited_subject = row['subject']
    if edited_body is None:
        edited_body = row['body_text'] or None

    # Load email from raw_path (legacy) or raw_content (new UID-based fetch)
    raw_path = row['raw_path']
    raw_content = row['raw_content']
    if raw_path and os.path.exists(raw_path):
        with open(raw_path,'rb') as f: original_bytes = f.read()
    elif raw_content:
        original_bytes = raw_content.encode('utf-8') if isinstance(raw_content, str) else raw_content
    else:
        conn.close();
        log.error("[interception::release] raw content missing", extra={'email_id': msg_id})
        return jsonify({'ok':False,'reason':'raw-missing'}), 500

    msg = BytesParser(policy=default_policy).parsebytes(original_bytes)
    if edited_subject:
        msg.replace_header('Subject', edited_subject) if msg['Subject'] else msg.add_header('Subject', edited_subject)
    if edited_body:
        if msg.is_multipart():
            # Update both text/plain and text/html parts to ensure clients display edits
            updated_plain = False; updated_html = False
            html_body = edited_body.replace('\n', '<br>')
            for part in msg.walk():
                if part.is_multipart():
                    continue
                ctype = (part.get_content_type() or '').lower()
                try:
                    if ctype == 'text/plain' and not updated_plain:
                        part.set_content(edited_body)
                        updated_plain = True
                    elif ctype == 'text/html' and not updated_html:
                        part.set_content(f"<div>{html_body}</div>", subtype='html')
                        updated_html = True
                except Exception:
                    pass
        else:
            from email.message import EmailMessage
            new_msg = EmailMessage();
            for k,v in msg.items():
                if k.lower() != 'content-type': new_msg[k] = v
            # Provide both plain and basic HTML alternatives
            new_msg.set_content(edited_body)
            try:
                new_msg.add_alternative(f"<div>{edited_body.replace('\n','<br>')}</div>", subtype='html')
            except Exception:
                pass
            msg = new_msg
    removed = []
    if strip_attachments and msg.is_multipart():
        from email.message import EmailMessage

        new_container = EmailMessage()
        for k, v in msg.items():
            if k.lower() in {'content-type', 'content-transfer-encoding', 'mime-version'}:
                continue
            new_container[k] = v

        plain_body = None
        html_body = None

        for part in msg.walk():
            if part.is_multipart():
                continue
            disp = (part.get_content_disposition() or '').lower()
            if disp == 'attachment':
                removed.append(part.get_filename() or 'attachment.bin')
                continue

            ctype = part.get_content_type()
            content = part.get_content()
            charset = part.get_content_charset()

            if ctype == 'text/plain' and plain_body is None:
                plain_body = (content, charset)
            elif ctype == 'text/html' and html_body is None:
                html_body = (content, charset)

        if removed:
            notice = '\n\n[Attachments removed: ' + ', '.join(removed) + ']'
            if plain_body is not None:
                plain_body = (plain_body[0] + notice, plain_body[1])
            else:
                plain_body = (notice.strip(), 'utf-8')

        plain_added = False
        try:
            if plain_body is not None:
                content, charset = plain_body
                if charset:
                    new_container.set_content(content, subtype='plain', charset=charset)
                else:
                    new_container.set_content(content)
                plain_added = True
            elif html_body is not None:
                content, charset = html_body
                if charset:
                    new_container.set_content(content, subtype='html', charset=charset)
                else:
                    new_container.set_content(content, subtype='html')
            else:
                new_container.set_content('Attachments removed', subtype='plain')
        except Exception as e:
            log.warning("[interception::release] Failed to build stripped message body", extra={'email_id': msg_id, 'error': str(e)})
            new_container.set_content('Attachments removed', subtype='plain')

        if plain_added and html_body is not None:
            content, charset = html_body
            try:
                if charset:
                    new_container.add_alternative(content, subtype='html', charset=charset)
                else:
                    new_container.add_alternative(content, subtype='html')
            except Exception as e:
                log.warning("[interception::release] Failed to add HTML alternative", extra={'email_id': msg_id, 'error': str(e)})

        msg = new_container
    decrypted_pass = decrypt_credential(row['imap_password'])
    try:
        if row['imap_use_ssl']:
            imap = imaplib.IMAP4_SSL(row['imap_host'], int(row['imap_port']))
        else:
            imap = imaplib.IMAP4(row['imap_host'], int(row['imap_port']))
        if not decrypted_pass: raise RuntimeError('Decrypted password missing')
        imap.login(row['imap_username'], decrypted_pass)
        status,_ = imap.select(target_folder)
        if status != 'OK': imap.select('INBOX')
        original_message_id = (row['message_id'] or '').strip()
        message_id_hdr = (msg.get('Message-ID') or '').strip()
        # Ensure Message-ID exists and is unique when edits were applied
        if message_id_hdr:
            if (edited_subject is not None or edited_body is not None or strip_attachments):
                new_mid = make_msgid()
                msg.replace_header('Message-ID', new_mid)
                message_id_hdr = new_mid.strip()
        else:
            new_mid = make_msgid()
            msg['Message-ID'] = new_mid
            message_id_hdr = new_mid.strip()

        # Use internaldate if available; else use current time; format via IMAP internal date
        date_param = None
        try:
            if row['original_internaldate']:
                from datetime import datetime as _dt
                try:
                    dt = _dt.fromisoformat(str(row['original_internaldate']))
                    date_param = imaplib.Time2Internaldate(dt.timetuple())
                except Exception:
                    date_param = None
            if not date_param:
                import time as _t
                date_param = imaplib.Time2Internaldate(_t.localtime())
        except Exception:
            import time as _t
            date_param = imaplib.Time2Internaldate(_t.localtime())
        # Idempotency guard: if a message with same Message-ID already exists, skip APPEND
        already_present = False
        try:
            if message_id_hdr:
                imap.select(target_folder)
                typ0, data0 = imap.search(None, 'HEADER', 'Message-ID', f"{message_id_hdr}")
                already_present = bool(data0 and data0[0] and len(data0[0].split()) > 0)
        except Exception:
            already_present = False

        release_marker = f"emt-release-{msg_id}"
        if msg.get(RELEASE_BYPASS_HEADER):
            del msg[RELEASE_BYPASS_HEADER]
        msg[RELEASE_BYPASS_HEADER] = release_marker
        if msg.get(RELEASE_EMAIL_ID_HEADER):
            del msg[RELEASE_EMAIL_ID_HEADER]
        msg[RELEASE_EMAIL_ID_HEADER] = str(msg_id)

        if not already_present:
            # Append the (possibly edited) message
            imap.append(target_folder, '', date_param, msg.as_bytes())

        # Verify delivery using Message-ID header
        verify_ok = True
        try:
            if message_id_hdr:
                imap.select(target_folder)
                typ, data = imap.search(None, 'HEADER', 'Message-ID', f"{message_id_hdr}")
                found = data and data[0] and len(data[0].split()) > 0
                verify_ok = bool(found)
        except Exception:
            # If verification fails unexpectedly, mark as failed
            verify_ok = False

        if not verify_ok:
            try: imap.logout()
            except Exception as e:
                log.debug("[interception::release] IMAP logout failed during verify failure (non-critical)", extra={'email_id': msg_id, 'error': str(e)})
            conn.close(); return jsonify({'ok': False, 'reason': 'verify-failed'}), 502

        # CRITICAL: Remove email from Quarantine folder after successful release to INBOX
        # This prevents duplicates and ensures only the edited version is in INBOX
        original_uid = row['original_uid']
        removed_from_quarantine = False
        header_candidates = []
        for candidate in (message_id_hdr, original_message_id):
            if candidate and candidate not in header_candidates:
                header_candidates.append(candidate)
        log.info(f"[interception::release] Attempting Quarantine cleanup for email {msg_id}, original_uid={original_uid}")

        def _delete_matches(uids):
            deleted = False
            for uid in uids:
                try:
                    uid_param = str(uid).strip()
                    if not uid_param:
                        continue
                    imap.uid('STORE', uid_param, '+FLAGS', '(\\Deleted)')
                    deleted = True
                except Exception as store_err:
                    log.debug("[interception::release] UID STORE failed uid=%s err=%s", uid, store_err)
            if deleted:
                try:
                    imap.expunge()
                except Exception as expunge_err:
                    log.debug("[interception::release] EXPUNGE failed err=%s", expunge_err)
            return deleted

        quarantine_candidates = [
            'Quarantine',
            'INBOX/Quarantine',
            'INBOX.Quarantine'
        ]

        def _extract_uids(search_segments):
            results = []
            if not search_segments:
                return results
            for segment in search_segments:
                if not segment:
                    continue
                if isinstance(segment, bytes):
                    segment = segment.decode('ascii', errors='ignore')
                if isinstance(segment, str):
                    parts = [item.strip() for item in segment.split() if item]
                    results.extend(parts)
            return results

        try:
            for qfolder in quarantine_candidates:
                try:
                    log.debug(f"[interception::release] Trying to select folder: {qfolder}")
                    status, data = imap.select(qfolder)
                    if status != 'OK':
                        continue

                    candidate_uids = []
                    for header_val in header_candidates:
                        try:
                            typ, search_data = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', header_val)
                            if typ == 'OK':
                                candidate_uids.extend(_extract_uids(search_data))
                        except Exception as search_err:
                            log.debug("[interception::release] HEADER search failed in %s (%s)", qfolder, search_err)

                    if not candidate_uids and original_uid:
                        try:
                            typ_uid, search_uid = imap.uid('SEARCH', None, 'UID', str(original_uid))
                            if typ_uid == 'OK':
                                candidate_uids.extend(_extract_uids(search_uid))
                        except Exception as uid_err:
                            log.debug("[interception::release] UID search failed in %s (%s)", qfolder, uid_err)

                    if candidate_uids:
                        candidate_uids = list(dict.fromkeys(candidate_uids))
                        if _delete_matches(candidate_uids):
                            removed_from_quarantine = True
                            log.info("[interception::release] Removed %d message(s) from %s", len(candidate_uids), qfolder, extra={'email_id': msg_id, 'uids': candidate_uids})
                            break
                except Exception as e:
                    log.warning(f"[interception::release] Folder {qfolder} not accessible: {e}", extra={'email_id': msg_id, 'folder': qfolder})
                    continue

            if not removed_from_quarantine:
                log.warning(f"[interception::release] Could not remove original message from quarantine (uid={original_uid})", extra={'email_id': msg_id, 'message_ids': header_candidates})

        except Exception as e:
            log.error(f"[interception::release] Failed to remove from quarantine: {e}", extra={'email_id': msg_id, 'uid': original_uid}, exc_info=True)

        # Reselect target folder for subsequent operations
        try:
            imap.select(target_folder)
        except Exception:
            pass

        # All good; close IMAP
        imap.logout()
    except Exception as e:
        log.exception("[interception::release] append failed", extra={'email_id': msg_id, 'target': target_folder})
        conn.close(); return jsonify({'ok':False,'reason':'append-failed','error':str(e)}), 500
    cur.execute("""
        UPDATE email_messages
        SET interception_status='RELEASED',
            status='DELIVERED',
            edited_message_id=?,
            processed_at=datetime('now'),
            action_taken_at=datetime('now')
        WHERE id=?
    """, (msg.get('Message-ID'), msg_id))
    conn.commit(); conn.close()
    # Best-effort audit
    try:
        log_action('RELEASE', getattr(current_user, 'id', None), msg_id, f"Released to {target_folder}; edited={bool(edited_subject or edited_body)}; removed={removed}")
    except Exception:
        pass
    log.info("[interception::release] success", extra={'email_id': msg_id, 'target': target_folder, 'attachments_removed': bool(removed)})
    return jsonify({'ok':True,'released_to':target_folder,'attachments_removed':removed})

@bp_interception.route('/api/interception/discard/<int:msg_id>', methods=['POST'])
@login_required
def api_interception_discard(msg_id:int):
    """Idempotent discard: if already DISCARDED (or not HELD), respond ok with no-op.
    Returns JSON: { ok: true, status: <current|DISCARDED>, changed: 0|1 }
    """
    conn = _db(); cur = conn.cursor()
    row = cur.execute("SELECT interception_status FROM email_messages WHERE id=?", (msg_id,)).fetchone()
    if not row:
        conn.close();
        return jsonify({'ok': False, 'reason': 'not-found'}), 404
    status = row['interception_status']
    if status == 'DISCARDED':
        conn.close();
        return jsonify({'ok': True, 'status': 'DISCARDED', 'changed': 0, 'already': True})
    if status != 'HELD':
        # No state change needed; treat as idempotent no-op
        conn.close();
        return jsonify({'ok': True, 'status': status, 'changed': 0, 'noop': True})
    # Transition HELD -> DISCARDED
    cur.execute("UPDATE email_messages SET interception_status='DISCARDED', action_taken_at=datetime('now') WHERE id=?", (msg_id,))
    changed = cur.rowcount or 0
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'status': 'DISCARDED', 'changed': int(changed)})

@bp_interception.route('/api/inbox')
@login_required
def api_inbox():
    status_filter = request.args.get('status','').strip().upper() or None
    q = (request.args.get('q') or '').strip()
    conn = _db(); cur = conn.cursor(); params=[]; clauses=[]
    if status_filter:
        clauses.append("(interception_status = ? OR status = ?)"); params.extend([status_filter,status_filter])
    if q:
        like=f"%{q}%"; clauses.append("(sender LIKE ? OR subject LIKE ?)"); params.extend([like,like])
    where = ('WHERE '+ ' AND '.join(clauses)) if clauses else ''
    rows = cur.execute(f"""
        SELECT id, sender, recipients, subject, interception_status, status, created_at, latency_ms, body_text, raw_path
        FROM email_messages
        {where}
        ORDER BY id DESC LIMIT 200
    """, params).fetchall()
    msgs=[]
    for r in rows:
        d=dict(r); body_txt=(d.get('body_text') or '')
        d['preview_snippet']=' '.join(body_txt.split())[:160]
        msgs.append(d)
    conn.close(); return jsonify({'messages':msgs,'count':len(msgs)})

@bp_interception.route('/api/email/<int:email_id>/edit', methods=['POST'])
@csrf.exempt
@limiter.limit(_EDIT_LIMIT_STRING)
@simple_rate_limit('edit', config=_EDIT_RATE_LIMIT)
@login_required
def api_email_edit(email_id:int):
    payload = request.get_json(silent=True) or {}
    subject = payload.get('subject'); body_text = payload.get('body_text'); body_html = payload.get('body_html')
    if not any([subject, body_text, body_html]):
        return jsonify({'ok':False,'error':'no-fields'}), 400
    conn = _db(); cur = conn.cursor()
    row = cur.execute("SELECT id, interception_status FROM email_messages WHERE id=?", (email_id,)).fetchone()
    if not row: conn.close(); return jsonify({'ok':False,'error':'not-found'}), 404
    if row['interception_status'] != 'HELD': conn.close(); return jsonify({'ok':False,'error':'not-held'}), 409
    fields=[]; values=[]
    if subject is not None: fields.append('subject = ?'); values.append(subject)
    if body_text is not None: fields.append('body_text = ?'); values.append(body_text)
    if body_html is not None: fields.append('body_html = ?'); values.append(body_html)
    values.append(email_id)
    cur.execute(f"UPDATE email_messages SET {', '.join(fields)}, updated_at = datetime('now') WHERE id = ?", values)
    conn.commit()
    # Re-read to verify persistence
    verify = cur.execute("SELECT id, subject, body_text, body_html FROM email_messages WHERE id = ?", (email_id,)).fetchone()
    result = {'ok': True, 'updated_fields': [f.split('=')[0].strip() for f in fields]}
    if verify:
        result['verified'] = {k: verify[k] for k in verify.keys()}
    conn.close()
    # Best-effort audit
    try:
        log_action('EDIT', getattr(current_user, 'id', None), email_id, f"Updated fields: {', '.join(result.get('updated_fields', []))}")
    except Exception:
        pass
    return jsonify(result)


@bp_interception.route('/api/email/<int:email_id>/intercept', methods=['POST'])
@csrf.exempt
@login_required
def api_email_intercept(email_id:int):
    """Manually intercept an email with remote MOVE to Quarantine folder (migrated)."""
    conn = _db(); cur = conn.cursor()
    row = cur.execute(
        """
        SELECT em.*, ea.imap_host, ea.imap_port, ea.imap_username, ea.imap_password
        FROM email_messages em
        LEFT JOIN email_accounts ea ON em.account_id = ea.id
        WHERE em.id=?
        """,
        (email_id,),
    ).fetchone()
    if not row:
        conn.close(); return jsonify({'success': False, 'error': 'Not found'}), 404
    if not row['account_id']:
        conn.close(); return jsonify({'success': False, 'error': 'No linked account'}), 400

    previous = (row['interception_status'] or '').upper()
    if previous == 'HELD':
        conn.close()
        return jsonify({'success': True, 'email_id': email_id, 'remote_move': False, 'previous_status': previous, 'note': 'already-held'})

    remote_move = False
    note = None
    effective_quarantine = row['quarantine_folder'] if 'quarantine_folder' in row.keys() and row['quarantine_folder'] else 'Quarantine'
    resolved_uid = row['original_uid']
    log.debug("[interception::manual_intercept] begin", extra={'email_id': email_id, 'account_id': row['account_id'], 'previous_status': previous, 'resolved_uid': resolved_uid})

    try:
        host = row['imap_host']; port = int(row['imap_port'] or 993)
        username = row['imap_username']; password = decrypt_credential(row['imap_password'])
        if not password:
            raise RuntimeError('Decrypted password missing')
        imap_obj = imaplib.IMAP4_SSL(host, port) if port == 993 else imaplib.IMAP4(host, port)
        try:
            if port != 993:
                imap_obj.starttls()
        except Exception:
            pass
        imap_obj.login(username, password)
        try:
            imap_obj.select('INBOX')
        except Exception:
            imap_obj.select()

        effective_quarantine = _ensure_quarantine(imap_obj, effective_quarantine)

        def _search_uid(header: str, value: Optional[str]) -> Optional[str]:
            if not header or not value:
                return None
            for candidate in (value, f'"{value}"'):
                try:
                    typ, data = cast(Any, imap_obj).uid('SEARCH', None, 'HEADER', header, candidate)
                    if typ == 'OK' and data and data[0]:
                        parts = data[0].split()
                        if parts:
                            last = parts[-1]
                            return last.decode() if isinstance(last, bytes) else str(last)
                except Exception:
                    continue
            return None

        def _search_gmail_rfc(msg_id: Optional[str]) -> Optional[str]:
            if not msg_id or 'gmail' not in (host or '').lower():
                return None
            query = f'rfc822msgid:{msg_id}'
            try:
                typ, data = cast(Any, imap_obj).uid('SEARCH', None, 'X-GM-RAW', query)
                if typ == 'OK' and data and data[0]:
                    parts = data[0].split()
                    if parts:
                        last = parts[-1]
                        return last.decode() if isinstance(last, bytes) else str(last)
            except Exception:
                return None
            return None

        if not resolved_uid and row['message_id']:
            resolved_uid = _search_uid('Message-ID', row['message_id'])
        if not resolved_uid and row['subject']:
            resolved_uid = _search_uid('Subject', row['subject'])
        if not resolved_uid and row['message_id']:
            resolved_uid = _search_gmail_rfc(row['message_id'])

        if resolved_uid:
            uid_str = str(resolved_uid)
            log.debug("[interception::manual_intercept] moving message", extra={'email_id': email_id, 'uid': uid_str, 'target': effective_quarantine})
            remote_move = _move_uid_to_quarantine(imap_obj, uid_str, effective_quarantine)
        else:
            note = 'Remote UID not found for manual intercept'
            log.warning("[interception::manual_intercept] UID not resolved", extra={'email_id': email_id, 'account_id': row['account_id']})

        try:
            imap_obj.logout()
        except Exception:
            pass
    except Exception as exc:
        note = f'IMAP error: {exc}'

    if not remote_move:
        conn.close()
        status_code = 502 if note and 'error' in note.lower() else 409
        log.warning("[interception::manual_intercept] move failed", extra={'email_id': email_id, 'account_id': row['account_id'], 'note': note, 'status_code': status_code})
        return jsonify({'success': False, 'email_id': email_id, 'remote_move': False, 'previous_status': previous, 'note': note or 'Remote move failed'}), status_code

    if resolved_uid and not row['original_uid']:
        cur.execute('UPDATE email_messages SET original_uid=? WHERE id=?', (int(resolved_uid), email_id))

    cur.execute(
        """
        UPDATE email_messages
        SET interception_status='HELD',
            status='PENDING',
            quarantine_folder=?,
            action_taken_at=datetime('now')
        WHERE id=?
        """,
        (effective_quarantine, email_id),
    ); conn.commit()
    log.info("[interception::manual_intercept] success", extra={'email_id': email_id, 'account_id': row['account_id'], 'quarantine_folder': effective_quarantine})

    # Calculate latency_ms best-effort
    try:
        row_t = cur.execute("SELECT created_at, action_taken_at, latency_ms FROM email_messages WHERE id=?", (email_id,)).fetchone()
        if row_t and row_t['created_at'] and row_t['action_taken_at'] and row_t['latency_ms'] is None:
            cur.execute("UPDATE email_messages SET latency_ms = CAST((julianday(action_taken_at) - julianday(created_at)) * 86400000 AS INTEGER) WHERE id=?", (email_id,))
            conn.commit()
    except Exception:
        pass
    conn.close()

    # Best-effort audit log
    try:
        from app.services.audit import log_action
        user_id = getattr(current_user, 'id', None)
        log_action('MANUAL_INTERCEPT', user_id, email_id, f"Manual intercept: remote_move={remote_move}, previous_status={previous}{', note='+note if note else ''}")
    except Exception:
        pass

    return jsonify({'success': True, 'email_id': email_id, 'remote_move': True, 'previous_status': previous, 'note': note, 'quarantine_folder': effective_quarantine})
