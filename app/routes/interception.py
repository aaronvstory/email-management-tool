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
import re
import sys
import traceback
import hashlib
from pathlib import Path
import json

from typing import Dict, Any, Optional, cast, Iterable
from flask import Blueprint, jsonify, render_template, request, current_app, send_file, abort
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

_FILENAME_SANITIZER = re.compile(r'[^A-Za-z0-9._-]+')


def _get_storage_roots() -> tuple[Path, Path]:
    """Return absolute paths for attachments and staged roots."""
    app = current_app
    attachments_root = Path(app.config.get('ATTACHMENTS_ROOT_DIR', 'attachments')).resolve()
    staged_root = Path(app.config.get('ATTACHMENTS_STAGED_ROOT_DIR', 'attachments_staged')).resolve()
    attachments_root.mkdir(parents=True, exist_ok=True)
    staged_root.mkdir(parents=True, exist_ok=True)
    return attachments_root, staged_root


def _sanitize_filename(value: Optional[str]) -> str:
    if not value:
        return 'attachment'
    candidate = value.strip().replace('\\', '_').replace('/', '_')
    sanitized = _FILENAME_SANITIZER.sub('_', candidate)
    sanitized = sanitized.strip('._')
    return sanitized[:255] or 'attachment'


def _is_under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _serialize_attachment_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        'id': row['id'],
        'email_id': row['email_id'],
        'filename': row['filename'],
        'mime_type': row['mime_type'],
        'size': row['size'],
        'sha256': row['sha256'],
        'disposition': row['disposition'],
        'content_id': row['content_id'],
        'is_original': bool(row['is_original']),
        'is_staged': bool(row['is_staged']),
    }


def _attachments_feature_enabled(flag: str) -> bool:
    return bool(current_app.config.get(flag, False))


def _ensure_attachments_extracted(conn: sqlite3.Connection, row: sqlite3.Row) -> Iterable[sqlite3.Row]:
    """Ensure original attachments for the given email are extracted to disk and recorded."""
    email_id = row['id']
    cur = conn.cursor()
    existing = cur.execute(
        "SELECT * FROM email_attachments WHERE email_id=? AND is_original=1 ORDER BY id",
        (email_id,),
    ).fetchall()
    if existing:
        return existing

    raw_bytes = None
    raw_path = row['raw_path']
    raw_content = row['raw_content']
    if raw_path and os.path.exists(raw_path):
        try:
            raw_bytes = Path(raw_path).read_bytes()
        except Exception as exc:
            log.warning("[attachments] Failed reading raw_path", extra={'email_id': email_id, 'error': str(exc)})
    if raw_bytes is None and raw_content:
        raw_bytes = raw_content if isinstance(raw_content, bytes) else raw_content.encode('utf-8', 'ignore')

    if not raw_bytes:
        return existing

    try:
        message = BytesParser(policy=default_policy).parsebytes(raw_bytes)
    except Exception as exc:
        log.warning("[attachments] Failed parsing raw email", extra={'email_id': email_id, 'error': str(exc)})
        return existing

    attachments_root, _ = _get_storage_roots()
    email_dir = attachments_root / str(email_id)
    try:
        email_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        log.warning("[attachments] Failed to create storage directory", extra={'email_id': email_id, 'error': str(exc)})
        return existing

    counter = 0
    for part in message.walk():
        if part.is_multipart():
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        disposition = (part.get_content_disposition() or '').lower() or None
        filename = part.get_filename()
        content_id = part.get('Content-ID')
        if not filename and disposition != 'attachment' and not content_id:
            # Skip inline body parts without filenames
            continue

        counter += 1
        base_name = _sanitize_filename(filename) if filename else f'attachment-{counter}'
        mime_type = part.get_content_type() or 'application/octet-stream'
        if '.' not in base_name:
            subtype = mime_type.split('/')[-1] if '/' in mime_type else None
            if subtype and subtype not in ('plain', 'html'):
                base_name = f'{base_name}.{subtype.lower()}'

        final_name = base_name
        suffix_count = 1
        while (email_dir / final_name).exists():
            path_obj = Path(base_name)
            final_name = f"{path_obj.stem}_{suffix_count}{path_obj.suffix}"
            suffix_count += 1

        destination = email_dir / final_name
        try:
            destination.write_bytes(payload)
        except Exception as exc:
            log.warning("[attachments] Failed writing attachment", extra={'email_id': email_id, 'file': final_name, 'error': str(exc)})
            continue

        sha256 = hashlib.sha256(payload).hexdigest()
        cur.execute(
            """
            INSERT OR IGNORE INTO email_attachments
                (email_id, filename, mime_type, size, sha256, disposition, content_id, is_original, is_staged, storage_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
            """,
            (
                email_id,
                final_name,
                mime_type,
                len(payload),
                sha256,
                disposition,
                (content_id or '').strip('<>') if content_id else None,
                str(destination),
            ),
        )

    conn.commit()
    return cur.execute(
        "SELECT * FROM email_attachments WHERE email_id=? AND is_original=1 ORDER BY id",
        (email_id,),
    ).fetchall()

SMTP_HOST = os.environ.get('SMTP_PROXY_HOST', '127.0.0.1')
SMTP_PORT = int(os.environ.get('SMTP_PROXY_PORT', '8587'))


# =============================================================================
# Helper Functions for IMAP Operations and Gmail-specific Searches
# =============================================================================

def _server_supports_x_gm(imap_conn):
    """Check if server supports Gmail extensions (X-GM-EXT-1)."""
    try:
        typ, data = imap_conn.capability()
        caps = b' '.join(data).upper() if data else b''
        return b'X-GM-EXT-1' in caps
    except:
        return False

def _uid_store(imap_conn, uid, op, labels):
    """Wrapper for UID STORE operations with error handling."""
    try:
        return imap_conn.uid('STORE', str(uid), op, labels)
    except Exception as e:
        log.debug(f"[_uid_store] Failed uid={uid} op={op}: {e}")
        return ('NO', [])

def _gm_search(imap_conn, raw_query):
    """Gmail X-GM-RAW search (must be called after select())."""
    try:
        typ, data = imap_conn.uid('SEARCH', None, 'X-GM-RAW', raw_query)
        if typ != 'OK' or not data or not data[0]:
            return []
        return [int(x) for x in data[0].split()]
    except Exception as e:
        log.debug(f"[_gm_search] Failed query={raw_query}: {e}")
        return []

def _gm_fetch_thrid(imap_conn, uid):
    """Fetch Gmail thread ID for a given UID (current mailbox)."""
    if not uid:
        return None
    try:
        typ, data = imap_conn.uid('FETCH', str(uid), '(X-GM-THRID)')
        if typ != 'OK' or not data or data[0] is None:
            return None
        # Parse: b'393 (X-GM-THRID 1760901299040 UID 393)'
        raw = data[0][1] if isinstance(data[0], tuple) else data[0]
        m = re.search(rb'X-GM-THRID\s+(\d+)', raw)
        return m.group(1).decode() if m else None
    except Exception as e:
        log.debug(f"[_gm_fetch_thrid] Failed uid={uid}: {e}")
        return None

def _find_uid_by_message_id(imap_conn, mailbox, msgid):
    """Find UID by Message-ID header (single result expected)."""
    try:
        imap_conn.select(mailbox)
        typ, data = imap_conn.uid('SEARCH', None, 'HEADER', 'Message-ID', f'"{msgid}"')
        if typ == 'OK' and data and data[0]:
            uids = [int(x) for x in data[0].split()]
            return uids[0] if uids else None
    except:
        return None

def _robust_message_id_search(imap_conn, folder, message_id, is_gmail=False, tries=3, delay=0.4):
    """
    Searches for a message by Message-ID using multiple strategies with retry logic.
    Returns list of UIDs found, or empty list if not found.

    Tries in order (Gmail):
    1. HEADER X-Google-Original-Message-ID (Gmail rewrites invalid Message-IDs)
    2. X-GM-RAW combo search (rfc822msgid OR X-Google-Original-Message-ID)
    3. Gmail X-GM-RAW rfc822msgid search
    4. HEADER Message-ID variants (stripped/original/quoted)

    Tries in order (Non-Gmail):
    1. HEADER Message-ID with stripped angle brackets
    2. HEADER Message-ID with original format
    3. HEADER Message-ID with quoted format

    Retries up to 'tries' times with 'delay' seconds between attempts to handle Gmail indexing lag.
    """
    if not message_id:
        return []

    mid = message_id.strip()
    stripped = mid.strip('<>').strip().replace('"', '')  # Sanitize to prevent search syntax injection
    quoted = f'"{mid}"'

    def _one_try():
        """Single attempt through all search strategies."""
        strategies = []

        # Gmail-specific strategies (highest confidence first)
        if is_gmail:
            # Gmail rewrites invalid Message-IDs and stores original in X-Google-Original-Message-ID
            strategies.append(('HEADER-XGOOG', stripped, 'HEADER X-Google-Original-Message-ID'))
            # Combo search: catches both rewritten and non-rewritten cases
            strategies.append(('X-GM-RAW', f'(rfc822msgid:{stripped} OR header:x-google-original-message-id:{stripped})', 'X-GM-RAW combo'))
            # Original X-GM-RAW rfc822msgid (for non-rewritten Message-IDs)
            strategies.append(('X-GM-RAW', f'rfc822msgid:{stripped}', 'Gmail X-GM-RAW rfc822msgid'))

        # Generic HEADER searches (work on Hostinger and other IMAP servers)
        strategies.extend([
            ('HEADER', stripped, 'HEADER (stripped)'),
            ('HEADER', mid, 'HEADER (original)'),
            ('HEADER', quoted, 'HEADER (quoted)'),
        ])

        for kind, arg, label in strategies:
            try:
                if kind == 'X-GM-RAW':
                    typ, data = imap_conn.uid('SEARCH', None, 'X-GM-RAW', arg)
                elif kind == 'HEADER-XGOOG':
                    typ, data = imap_conn.uid('SEARCH', None, 'HEADER', 'X-Google-Original-Message-ID', arg)
                else:
                    typ, data = imap_conn.uid('SEARCH', None, kind, 'Message-ID', arg)

                log.info("[Search] Attempt", extra={"kind": kind, "label": label, "typ": typ, "raw": str(data)[:200], "folder": folder})

                if typ == 'OK' and data and data[0]:
                    uids = [u.decode() if isinstance(u, bytes) else u for u in data[0].split()]
                    if uids:
                        log.info("[Search] SUCCESS", extra={"label": label, "uids": uids, "folder": folder})
                        return uids
            except Exception as e:
                log.debug("[Search] Error", extra={"label": label, "err": str(e)})
        return []

    # Retry loop to handle Gmail indexing lag with exponential backoff
    for attempt in range(max(1, tries)):
        if attempt > 0:
            # Exponential backoff: 0.25s, 0.5s, 1s for better Gmail indexing lag handling
            backoff_delay = delay * (2 ** (attempt - 1))
            log.info(f"[Search] Retry attempt {attempt + 1}/{tries}", extra={"folder": folder, "message_id": mid[:50], "backoff": backoff_delay})
            time.sleep(backoff_delay)

        uids = _one_try()
        if uids:
            return uids

    log.warning("[Search] FAILED all strategies after retries", extra={"message_id": mid, "folder": folder, "tries": tries})
    return []


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
          AND sender != 'selfcheck@localhost'
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

@bp_interception.route('/api/email/<int:email_id>/attachments', methods=['GET'])
@login_required
def api_email_attachments(email_id: int):
    if not _attachments_feature_enabled('ATTACHMENTS_UI_ENABLED'):
        return jsonify({'ok': False, 'error': 'disabled'}), 403

    conn = _db()
    try:
        row = conn.execute("SELECT * FROM email_messages WHERE id=?", (email_id,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'not-found'}), 404

        original_rows = list(_ensure_attachments_extracted(conn, row))
        manifest_raw = row['attachments_manifest'] if 'attachments_manifest' in row.keys() else None
        manifest = None
        if manifest_raw:
            try:
                manifest = json.loads(manifest_raw)
            except Exception as exc:
                log.warning("[attachments] Failed to decode manifest", extra={'email_id': email_id, 'error': str(exc)})

        version = row['version'] if 'version' in row.keys() and row['version'] is not None else 0
        payload = {
            'ok': True,
            'email_id': email_id,
            'version': version,
            'attachments': [_serialize_attachment_row(r) for r in original_rows],
            'manifest': manifest,
        }
        return jsonify(payload)
    finally:
        conn.close()


@bp_interception.route('/api/attachment/<int:attachment_id>/download', methods=['GET'])
@login_required
def api_attachment_download(attachment_id: int):
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM email_attachments WHERE id=?", (attachment_id,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'not-found'}), 404

        attachments_root, staged_root = _get_storage_roots()
        storage_path = Path(row['storage_path']).resolve()

        if not storage_path.exists() or not storage_path.is_file():
            log.warning("[attachments] File missing for download", extra={'attachment_id': attachment_id, 'path': str(storage_path)})
            return jsonify({'ok': False, 'error': 'not-found'}), 404

        if not (_is_under(storage_path, attachments_root) or _is_under(storage_path, staged_root)):
            log.warning("[attachments] Download path outside storage roots", extra={'attachment_id': attachment_id, 'path': str(storage_path)})
            abort(404)

        download_name = row['filename'] or f'attachment-{attachment_id}'
        mimetype = row['mime_type'] or 'application/octet-stream'
        return send_file(storage_path, mimetype=mimetype, as_attachment=True, download_name=download_name)
    finally:
        conn.close()

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

    app_log = logging.getLogger("simple_app")
    app_log.debug("Entered release handler", extra={"email_id": msg_id})

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

        # Add idempotency header to track which original this release came from
        if original_message_id:
            if 'X-EMT-Released-From' in msg:
                msg.replace_header('X-EMT-Released-From', original_message_id)
            else:
                msg['X-EMT-Released-From'] = original_message_id
            app_log.info("[Idempotency] Added X-EMT-Released-From header", extra={
                "email_id": msg_id,
                "original_message_id": original_message_id
            })

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

        app_log.debug("About to append edited message", extra={
            "email_id": msg_id,
            "target_folder": target_folder,
            "already_present": already_present,
        })

        # ========================================================================
        # PHASE A: PRE-APPEND CLEANUP - Delete original from Quarantine FIRST
        # ========================================================================
        # This prevents race conditions where original gets \Inbox label after append
        original_uid = row['original_uid']
        # sqlite3.Row doesn't have .get() - use try/except instead
        try:
            quarantine_folder = row['quarantine_folder'] if row['quarantine_folder'] else 'Quarantine'
        except (KeyError, TypeError):
            quarantine_folder = 'Quarantine'

        if original_uid:
            try:
                app_log.info("[Release] Phase A: Pre-append Quarantine cleanup", extra={
                    "email_id": msg_id, "original_uid": original_uid, "folder": quarantine_folder
                })

                # Select Quarantine folder
                typ, _ = imap.select(quarantine_folder)
                if typ == 'OK':
                    # Delete by UID (most reliable method)
                    imap.uid('STORE', str(original_uid), '+FLAGS', r'(\Deleted)')
                    imap.expunge()
                    app_log.info("[Release] Phase A: SUCCESS - Original deleted", extra={
                        "email_id": msg_id, "uid": original_uid
                    })
                else:
                    app_log.warning(f"[Release] Phase A: Failed to select {quarantine_folder}", extra={
                        "email_id": msg_id, "typ": typ
                    })
            except Exception as e:
                app_log.warning(f"[Release] Phase A: Quarantine cleanup failed", extra={
                    "email_id": msg_id, "error": str(e)
                })
        else:
            app_log.info("[Release] Phase A: No original_uid, skipping Quarantine delete",
                         extra={"email_id": msg_id})

        # Determine if this is Gmail for search optimization (do this early for Phase B backoff)
        try:
            host_l = str(row['imap_host'] if row['imap_host'] else '').lower()
        except (KeyError, TypeError):
            host_l = ''
        is_gmail = any(k in host_l for k in ("gmail", "googlemail", "google"))

        # ========================================================================
        # PHASE B: APPEND EDITED MESSAGE TO INBOX
        # ========================================================================
        if not already_present:
            app_log.info("[Release] Phase B: Appending edited message", extra={
                "email_id": msg_id, "target_folder": target_folder
            })
            # Append the (possibly edited) message
            append_result = imap.append(target_folder, '', date_param, msg.as_bytes())

            # Gmail index backoff: small delay to avoid rare indexing race conditions
            # Gmail's search index may lag by 100-300ms after APPEND
            if is_gmail:
                time.sleep(0.2)  # 200ms backoff for Gmail indexing
                app_log.info("[Release] Phase B: Gmail index backoff applied", extra={
                    "email_id": msg_id, "backoff_ms": 200
                })

        # ========================================================================
        # PHASE C: GMAIL THREAD-LEVEL CLEANUP (The Game Changer)
        # Uses X-GM-THRID to remove \Inbox label from ALL thread messages except edited
        # ========================================================================
        if is_gmail and _server_supports_x_gm(imap):
            try:
                app_log.info("[Release] Phase C: Gmail thread cleanup starting", extra={
                    "email_id": msg_id, "is_gmail": is_gmail
                })

                # Step 1: Find UID of newly appended edited message in INBOX
                imap.select(target_folder)
                edited_uid = None

                if message_id_hdr:
                    # Search for edited message by its Message-ID
                    typ, data = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', f'"{message_id_hdr}"')
                    if typ == 'OK' and data and data[0]:
                        uids = [int(x) for x in data[0].split()]
                        edited_uid = uids[0] if uids else None
                        app_log.info("[Release] Phase C: Found edited message UID", extra={
                            "email_id": msg_id, "edited_uid": edited_uid, "message_id": message_id_hdr
                        })

                if not edited_uid:
                    app_log.warning("[Release] Phase C: Could not find edited message UID, skipping thread cleanup",
                                  extra={"email_id": msg_id})
                else:
                    # Step 2: Fetch X-GM-THRID for the edited message
                    thread_id = _gm_fetch_thrid(imap, edited_uid)

                    if not thread_id:
                        app_log.warning("[Release] Phase C: Could not fetch thread ID", extra={
                            "email_id": msg_id, "edited_uid": edited_uid
                        })
                    else:
                        app_log.info("[Release] Phase C: Fetched thread ID", extra={
                            "email_id": msg_id, "thread_id": thread_id
                        })

                        # Step 3: Search All Mail for all messages in this thread
                        # Use X-GM-RAW "thread:<id>" - X-GM-THRID is FETCH-only, not SEARCH
                        imap.select('"[Gmail]/All Mail"')
                        typ, data = imap.uid('SEARCH', None, 'X-GM-RAW', f'"thread:{thread_id}"')

                        if typ == 'OK' and data and data[0]:
                            thread_uids = [int(x) for x in data[0].split()]
                            app_log.info("[Release] Phase C: Found thread messages in All Mail", extra={
                                "email_id": msg_id, "thread_id": thread_id, "count": len(thread_uids),
                                "uids": thread_uids
                            })

                            # Step 4: Remove \Inbox and Quarantine labels from ALL except edited message
                            # Note: We need to re-find the edited UID in All Mail context
                            imap.select('"[Gmail]/All Mail"')
                            edited_uid_in_allmail = None

                            if message_id_hdr:
                                typ2, data2 = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', f'"{message_id_hdr}"')
                                if typ2 == 'OK' and data2 and data2[0]:
                                    uids2 = [int(x) for x in data2[0].split()]
                                    edited_uid_in_allmail = uids2[0] if uids2 else None

                            removed_labels_count = 0
                            for uid in thread_uids:
                                # Skip the edited message itself
                                if edited_uid_in_allmail and uid == edited_uid_in_allmail:
                                    app_log.info("[Release] Phase C: Preserving edited message", extra={
                                        "email_id": msg_id, "uid": uid
                                    })
                                    continue

                                # Remove \Inbox and Quarantine labels from this message
                                # Enhancement: Fetch actual labels present and remove them intelligently
                                try:
                                    # Fetch current labels on this message
                                    labels_to_remove = []
                                    ftyp, fdat = imap.uid('FETCH', str(uid), '(X-GM-LABELS)')

                                    if ftyp == 'OK' and fdat and isinstance(fdat[0], tuple):
                                        raw = fdat[0][1].decode('utf-8', 'ignore') if isinstance(fdat[0][1], bytes) else str(fdat[0][1])
                                        app_log.info("[Release] Phase C: Fetched labels", extra={
                                            "email_id": msg_id, "uid": uid, "raw_labels": raw[:200]
                                        })

                                        # Parse labels: look for tokens that match Quarantine variants
                                        # Matches: "Quarantine", "[Gmail]/Quarantine", "INBOX/Quarantine", etc.
                                        for token in re.findall(r'"\[?[^"]+\]?"|\\\w+', raw):
                                            t = token.strip('"').strip()
                                            # Match Quarantine in any form
                                            if (t.lower() == 'quarantine' or
                                                t.endswith('/Quarantine') or
                                                t.endswith('.Quarantine') or
                                                'Quarantine' in t):
                                                labels_to_remove.append(t)
                                                app_log.info("[Release] Phase C: Found Quarantine label", extra={
                                                    "email_id": msg_id, "uid": uid, "label": t
                                                })

                                    # Always remove \Inbox label (use X-GM-LABELS for Gmail labels, not FLAGS)
                                    typ_store, _ = _uid_store(imap, uid, '-X-GM-LABELS', r'(\Inbox)')
                                    if typ_store == 'OK':
                                        removed_labels_count += 1
                                        app_log.info("[Release] Phase C: Removed \\Inbox from thread message", extra={
                                            "email_id": msg_id, "uid": uid
                                        })

                                    # Remove any Quarantine-like labels actually present
                                    for lb in labels_to_remove:
                                        typ_quar, _ = _uid_store(imap, uid, '-X-GM-LABELS', f'("{lb}")')
                                        if typ_quar == 'OK':
                                            removed_labels_count += 1
                                            app_log.info("[Release] Phase C: Removed Quarantine label", extra={
                                                "email_id": msg_id, "uid": uid, "label": lb
                                            })

                                except Exception as e:
                                    app_log.warning("[Release] Phase C: Failed to remove labels", extra={
                                        "email_id": msg_id, "uid": uid, "error": str(e)
                                    })

                            app_log.info("[Release] Phase C: SUCCESS - Thread cleanup complete", extra={
                                "email_id": msg_id, "thread_id": thread_id,
                                "processed": len(thread_uids),
                                "labels_removed": removed_labels_count
                            })
                        else:
                            app_log.warning("[Release] Phase C: No messages found in thread", extra={
                                "email_id": msg_id, "thread_id": thread_id
                            })

            except Exception as e:
                app_log.error("[Release] Phase C: Thread cleanup failed", extra={
                    "email_id": msg_id, "error": str(e), "traceback": traceback.format_exc()
                })
                # Don't fail the entire release if thread cleanup fails
                pass
        else:
            if is_gmail:
                app_log.info("[Release] Phase C: Skipped (Gmail extensions not supported)", extra={
                    "email_id": msg_id
                })
            else:
                app_log.info("[Release] Phase C: Skipped (not Gmail)", extra={
                    "email_id": msg_id, "is_gmail": is_gmail
                })

        # Failsafe INBOX cleanup to prevent visible duplicates
        # This runs even if All Mail purge fails, ensuring no duplicates in user's view
        try:
            typ, data = imap.select("INBOX", readonly=False)
            app_log.debug("INBOX select for failsafe cleanup", extra={
                "email_id": msg_id, "typ": typ, "is_gmail": is_gmail})

            if typ == "OK" and original_message_id:
                # Show INBOX state before search
                inbox_count = data[0].decode() if data and data[0] else "?"
                all_typ, all_data = imap.uid('SEARCH', None, 'ALL')
                all_uids = all_data[0].decode() if all_data and all_data[0] else ""
                uid_list = all_uids.split()[:5]  # First 5 UIDs for context

                app_log.debug("INBOX state before search", extra={
                    "email_id": msg_id,
                    "inbox_message_count": inbox_count,
                    "total_uids": len(all_uids.split()) if all_uids else 0,
                    "sample_uids": uid_list,
                    "searching_for_message_id": original_message_id
                })

                # Use robust multi-strategy search
                uids = _robust_message_id_search(imap, "INBOX", original_message_id, is_gmail=is_gmail)

                if uids:
                    app_log.info("[Failsafe] Found original in INBOX, removing", extra={
                        "email_id": msg_id, "uids": uids})

                    for uid in uids:
                        imap.uid('STORE', uid, '+FLAGS', r'(\Deleted)')
                    imap.expunge()

                    app_log.info("[Failsafe] Removed original from INBOX by UID/EXPUNGE", extra={
                        "email_id": msg_id, "uids": uids})
                else:
                    app_log.info("[Failsafe] No original found in INBOX (may already be cleaned or never existed there)",
                               extra={"email_id": msg_id})
        except Exception as e:
            app_log.warning("[Failsafe DEBUG] INBOX cleanup failed", extra={"email_id": msg_id, "error": str(e)})

        # ========================================================================
        # PHASE E: HARDENED VERIFICATION USING THREAD ID
        # Verify edited message exists AND no duplicates present
        # ========================================================================
        verify_ok = True
        duplicate_detected = False

        try:
            if message_id_hdr:
                app_log.info("[Release] Phase E: Starting verification", extra={
                    "email_id": msg_id, "is_gmail": is_gmail
                })

                # Step 1: Verify edited message exists in target folder (INBOX)
                imap.select(target_folder)
                typ, data = imap.search(None, 'HEADER', 'Message-ID', f"{message_id_hdr}")
                found = data and data[0] and len(data[0].split()) > 0
                verify_ok = bool(found)

                if verify_ok:
                    app_log.info("[Release] Phase E: Edited message verified in INBOX", extra={
                        "email_id": msg_id, "message_id": message_id_hdr
                    })
                else:
                    app_log.error("[Release] Phase E: Edited message NOT found in INBOX", extra={
                        "email_id": msg_id, "message_id": message_id_hdr
                    })

                # Step 2: Gmail thread-level duplicate detection
                if verify_ok and is_gmail and _server_supports_x_gm(imap):
                    try:
                        app_log.info("[Release] Phase E: Starting Gmail thread duplicate check", extra={
                            "email_id": msg_id
                        })

                        # Find edited message UID in INBOX
                        imap.select(target_folder)
                        typ, data = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', f'"{message_id_hdr}"')
                        edited_uid = None
                        if typ == 'OK' and data and data[0]:
                            uids = [int(x) for x in data[0].split()]
                            edited_uid = uids[0] if uids else None

                        if edited_uid:
                            # Get thread ID for edited message
                            thread_id = _gm_fetch_thrid(imap, edited_uid)

                            if thread_id:
                                app_log.info("[Release] Phase E: Got thread ID for verification", extra={
                                    "email_id": msg_id, "thread_id": thread_id
                                })

                                # Search INBOX for all messages in this thread
                                # Use X-GM-RAW "in:inbox thread:<id>" for precise INBOX-only search
                                imap.select("INBOX")
                                typ, data = imap.uid('SEARCH', None, 'X-GM-RAW', f'"in:inbox thread:{thread_id}"')

                                if typ == 'OK' and data and data[0]:
                                    inbox_thread_uids = [int(x) for x in data[0].split()]
                                    app_log.info("[Release] Phase E: Found thread messages in INBOX", extra={
                                        "email_id": msg_id, "count": len(inbox_thread_uids),
                                        "uids": inbox_thread_uids
                                    })

                                    # Verify only ONE message is in INBOX (the edited one)
                                    if len(inbox_thread_uids) > 1:
                                        duplicate_detected = True
                                        app_log.error("[Release] Phase E: DUPLICATE DETECTED - Multiple thread messages in INBOX", extra={
                                            "email_id": msg_id, "count": len(inbox_thread_uids),
                                            "uids": inbox_thread_uids, "expected_uid": edited_uid
                                        })
                                    elif len(inbox_thread_uids) == 1 and inbox_thread_uids[0] == edited_uid:
                                        app_log.info("[Release] Phase E: SUCCESS - Only edited message in INBOX", extra={
                                            "email_id": msg_id, "uid": edited_uid
                                        })
                                    else:
                                        app_log.warning("[Release] Phase E: Unexpected UID in INBOX", extra={
                                            "email_id": msg_id, "found_uids": inbox_thread_uids,
                                            "expected_uid": edited_uid
                                        })

                                # Step 3: Verify original Message-ID is NOT in INBOX
                                if original_message_id:
                                    imap.select("INBOX")
                                    typ, data = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', f'"{original_message_id}"')
                                    if typ == 'OK' and data and data[0]:
                                        original_found = [int(x) for x in data[0].split()]
                                        if original_found:
                                            duplicate_detected = True
                                            app_log.error("[Release] Phase E: ORIGINAL STILL IN INBOX", extra={
                                                "email_id": msg_id, "original_uids": original_found,
                                                "original_message_id": original_message_id
                                            })
                                        else:
                                            app_log.info("[Release] Phase E: Original correctly removed from INBOX", extra={
                                                "email_id": msg_id
                                            })
                            else:
                                app_log.warning("[Release] Phase E: Could not get thread ID for verification", extra={
                                    "email_id": msg_id
                                })
                        else:
                            app_log.warning("[Release] Phase E: Could not find edited UID for verification", extra={
                                "email_id": msg_id
                            })

                    except Exception as e:
                        app_log.warning("[Release] Phase E: Thread verification failed (non-fatal)", extra={
                            "email_id": msg_id, "error": str(e)
                        })
                        # Don't fail the release, just log the issue
                else:
                    app_log.info("[Release] Phase E: Thread verification skipped (not Gmail or no X-GM support)", extra={
                        "email_id": msg_id, "is_gmail": is_gmail
                    })

        except Exception as e:
            app_log.error("[Release] Phase E: Verification failed", extra={
                "email_id": msg_id, "error": str(e)
            })
            verify_ok = False

        # Log final verification status
        if duplicate_detected:
            app_log.error("[Release] Phase E: VERIFICATION COMPLETE - DUPLICATES DETECTED", extra={
                "email_id": msg_id, "verify_ok": verify_ok
            })
        elif verify_ok:
            app_log.info("[Release] Phase E: VERIFICATION COMPLETE - SUCCESS", extra={
                "email_id": msg_id
            })
        else:
            app_log.error("[Release] Phase E: VERIFICATION COMPLETE - FAILED", extra={
                "email_id": msg_id
            })

        if not verify_ok:
            try: imap.logout()
            except Exception as e:
                log.debug("[interception::release] IMAP logout failed during verify failure (non-critical)", extra={'email_id': msg_id, 'error': str(e)})
            conn.close(); return jsonify({'ok': False, 'reason': 'verify-failed'}), 502

        # CRITICAL: Remove any original copies from INBOX and Quarantine after successful release
        # This prevents duplicates and ensures only the edited version is in INBOX
        original_uid = row['original_uid']
        removed_from_quarantine = False
        removed_original_from_inbox = False
        
        # DEBUG: Verify we have the original Message-ID for cleanup
        edited_message_id = message_id_hdr
        app_log.info("[Gmail DEBUG] IDs", extra={
            "email_id": msg_id,
            "original_message_id": original_message_id,
            "edited_message_id": edited_message_id,
        })
        
        # Only target the original message identifiers for cleanup (never the newly appended edited message)
        header_candidates = []
        if original_message_id:
            header_candidates.append(original_message_id)
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

        # Prefer the recorded quarantine folder first (provider-specific), then common fallbacks
        quarantine_candidates = []
        try:
            if 'quarantine_folder' in row.keys() and row['quarantine_folder']:
                quarantine_candidates.append(row['quarantine_folder'])
        except Exception:
            pass
        quarantine_candidates.extend([
            'Quarantine',
            'INBOX/Quarantine',
            'INBOX.Quarantine'
        ])

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
            # 1) Proactively remove any original copy lingering in INBOX by Message-ID or original UID
            try:
                status_inbox, _ = imap.select('INBOX')
                if status_inbox == 'OK':
                    inbox_uids = []
                    # Try header search with and without quotes (original only)
                    for header_val in header_candidates:
                        for probe in (header_val, f'"{header_val}"'):
                            try:
                                t_in, d_in = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', probe)
                                if t_in == 'OK':
                                    inbox_uids.extend(_extract_uids(d_in))
                            except Exception:
                                continue
                    # Fallback to UID match if we have it
                    if not inbox_uids and original_uid:
                        try:
                            t_in2, d_in2 = imap.uid('SEARCH', None, 'UID', str(original_uid))
                            if t_in2 == 'OK':
                                inbox_uids.extend(_extract_uids(d_in2))
                        except Exception:
                            pass
                    if inbox_uids:
                        if _delete_matches(inbox_uids):
                            removed_original_from_inbox = True
            except Exception:
                pass

            # 2) Remove from Quarantine folder(s)
            for qfolder in quarantine_candidates:
                try:
                    log.debug(f"[interception::release] Trying to select folder: {qfolder}")
                    status, data = imap.select(qfolder)
                    if status != 'OK':
                        continue

                    candidate_uids = []
                    for header_val in header_candidates:
                        try:
                            # Try both raw and quoted header values for robustness across providers (esp. Gmail)
                            typ, search_data = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', header_val)
                            if typ == 'OK':
                                candidate_uids.extend(_extract_uids(search_data))
                            if not candidate_uids:
                                typq, search_data_q = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', f'"{header_val}"')
                                if typq == 'OK':
                                    candidate_uids.extend(_extract_uids(search_data_q))
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

            # 3) Gmail-specific label cleanup (best-effort) to ensure original cannot retain \Inbox label
            try:
                host_l = ''
                try:
                    if 'imap_host' in row.keys() and row['imap_host']:
                        host_l = str(row['imap_host']).lower()
                except Exception:
                    host_l = ''
                # Check capability when possible (non-fatal if unsupported)
                
                # DEBUG: Gate check to diagnose if Gmail purge block is considered
                is_gmail = any(k in host_l for k in ("gmail", "googlemail", "google"))
                app_log.info("[Gmail DEBUG] Gate check", extra={
                    "email_id": msg_id,
                    "imap_host": host_l,
                    "gmail_flag": str(os.getenv("GMAIL_ALL_MAIL_PURGE", "1")),
                    "has_headers": bool(header_candidates),
                    "is_gmail": is_gmail,
                })
                if is_gmail:
                    try:
                        imap.select('INBOX')
                        for header_val in header_candidates:
                            for probe in (header_val, f'"{header_val}"'):
                                t_gm, d_gm = imap.uid('SEARCH', None, 'HEADER', 'Message-ID', probe)
                                if t_gm != 'OK' or not d_gm:
                                    continue
                                gm_uids = _extract_uids(d_gm)
                                for uid in gm_uids:
                                    try:
                                        imap.uid('STORE', str(uid), '-X-GM-LABELS', '(\\Inbox)')
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                    
                    # 4) Gmail defense-in-depth: purge any remaining original from All Mail
                    # Can be disabled via GMAIL_ALL_MAIL_PURGE=0 for emergency rollback
                    gmail_purge_enabled = str(os.getenv('GMAIL_ALL_MAIL_PURGE', '1')).lower() in ('1', 'true', 'yes')
                    if header_candidates and gmail_purge_enabled:
                        def _discover_gmail_boxes(imap_obj):
                            """Discover All Mail and Trash using special-use flags with robust fallbacks."""
                            all_mail_name, trash_name = None, None
                            try:
                                typ, mailboxes = imap_obj.list()
                                if typ == 'OK' and mailboxes:
                                    for raw in mailboxes:
                                        line = raw.decode('utf-8', errors='ignore') if isinstance(raw, bytes) else raw
                                        # Robust parsing: handle variations in LIST response format
                                        if '\\All' in line:
                                            # Extract mailbox name (last quoted or unquoted segment)
                                            parts = line.split('"')
                                            all_mail_name = parts[-1] if len(parts) > 1 else line.split()[-1]
                                            all_mail_name = all_mail_name.strip('"').strip()
                                        if '\\Trash' in line:
                                            parts = line.split('"')
                                            trash_name = parts[-1] if len(parts) > 1 else line.split()[-1]
                                            trash_name = trash_name.strip('"').strip()
                            except Exception as e:
                                log.debug(f"[Gmail] Mailbox discovery failed: {e}", exc_info=False)

                            # Proper fallback: try discovery first, then English Gmail variant
                            if not all_mail_name:
                                all_mail_name = '[Gmail]/All Mail'
                            if not trash_name:
                                trash_name = '[Gmail]/Trash'

                            return all_mail_name, trash_name

                        all_mail_box, trash_box = _discover_gmail_boxes(imap)

                        # DEBUG: Log discovered mailboxes for live testing validation
                        log.info(f"[Gmail DEBUG] Discovered mailboxes: All Mail='{all_mail_box}', Trash='{trash_box}'",
                                 extra={'email_id': msg_id})

                        # Check for MOVE capability (RFC 6851) and UIDPLUS (RFC 4315)
                        caps = ()
                        try:
                            if hasattr(imap, 'capabilities') and imap.capabilities:
                                caps = imap.capabilities if isinstance(imap.capabilities, tuple) else ()
                        except Exception:
                            caps = ()

                        has_move = 'MOVE' in caps
                        has_uidplus = 'UIDPLUS' in caps

                        # DEBUG: Log capabilities for live testing validation
                        log.info(f"[Gmail DEBUG] IMAP capabilities: {caps}, MOVE={has_move}, UIDPLUS={has_uidplus}",
                                 extra={'email_id': msg_id})

                        # All Mail cleanup attempt
                        try:
                            typ, _ = imap.select(all_mail_box, readonly=False)
                            if typ != 'OK':
                                log.debug(f"[Gmail] All Mail select failed: {all_mail_box}")
                            else:
                                for hdr in header_candidates:
                                    try:
                                        # Use robust multi-strategy search for All Mail
                                        uids = _robust_message_id_search(imap, all_mail_box, hdr, is_gmail=True)

                                        # ========================================================================
                                        # PHASE D: ENHANCED ALL MAIL FALLBACK (Broadened Search)
                                        # If standard search fails, try additional Gmail-specific strategies
                                        # ========================================================================
                                        if not uids and _server_supports_x_gm(imap):
                                            app_log.debug("Phase D: Trying broadened All Mail search", extra={
                                                "email_id": msg_id, "hdr": hdr
                                            })

                                            # Strategy 1: Search by X-EMT-Released-From header (if this is an edited release)
                                            if original_message_id:
                                                try:
                                                    # Gmail X-GM-RAW uses: header:name "value" (space, then quoted value)
                                                    search_query = f'header:x-emt-released-from "{original_message_id.strip("<>")}"'
                                                    app_log.info("[Release] Phase D: Trying X-EMT-Released-From search", extra={
                                                        "email_id": msg_id, "query": search_query
                                                    })
                                                    typ, data = imap.uid('SEARCH', None, 'X-GM-RAW', search_query)
                                                    if typ == 'OK' and data and data[0]:
                                                        uids = [u.decode() if isinstance(u, bytes) else u for u in data[0].split()]
                                                        if uids:
                                                            app_log.info("[Release] Phase D: Found via X-EMT-Released-From", extra={
                                                                "email_id": msg_id, "uids": uids
                                                            })
                                                except Exception as e:
                                                    app_log.debug("[Release] Phase D: X-EMT-Released-From search failed", extra={
                                                        "email_id": msg_id, "error": str(e)
                                                    })

                                            # Strategy 2: Search by subject + from combination (broadened pattern)
                                            # sqlite3.Row doesn't have .get() - check keys() instead
                                            if (not uids and 'sender' in row.keys() and 'subject' in row.keys() and
                                                row['sender'] and row['subject']):
                                                try:
                                                    sender_email = row['sender']
                                                    subject_text = row['subject']
                                                    # Extract email from "Name <email>" format
                                                    if '<' in sender_email and '>' in sender_email:
                                                        sender_email = sender_email.split('<')[1].split('>')[0]
                                                    # Sanitize subject for search (remove special chars that break X-GM-RAW)
                                                    subject_clean = subject_text.replace('"', '').replace('\\', '').strip()[:50]

                                                    search_query = f'from:{sender_email} subject:"{subject_clean}"'
                                                    app_log.info("[Release] Phase D: Trying subject+sender search", extra={
                                                        "email_id": msg_id, "query": search_query
                                                    })
                                                    typ, data = imap.uid('SEARCH', None, 'X-GM-RAW', search_query)
                                                    if typ == 'OK' and data and data[0]:
                                                        candidate_uids = [u.decode() if isinstance(u, bytes) else u for u in data[0].split()]
                                                        # Verify we're not accidentally matching the edited message
                                                        # by checking it's not the Message-ID we just appended
                                                        verified_uids = []
                                                        for cuid in candidate_uids:
                                                            try:
                                                                fetch_typ, fetch_data = imap.uid('FETCH', str(cuid), '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')
                                                                if fetch_typ == 'OK' and fetch_data and fetch_data[0]:
                                                                    header_part = fetch_data[0][1] if isinstance(fetch_data[0], tuple) else fetch_data[0]
                                                                    if isinstance(header_part, bytes):
                                                                        header_str = header_part.decode('utf-8', errors='ignore')
                                                                        # Skip if this is the edited message we just appended
                                                                        if message_id_hdr and message_id_hdr in header_str:
                                                                            continue
                                                                        # Include if this looks like the original
                                                                        if original_message_id and original_message_id in header_str:
                                                                            verified_uids.append(cuid)
                                                            except Exception:
                                                                pass

                                                        if verified_uids:
                                                            uids = verified_uids
                                                            app_log.info("[Release] Phase D: Found via subject+sender", extra={
                                                                "email_id": msg_id, "uids": uids
                                                            })
                                                except Exception as e:
                                                    app_log.debug("[Release] Phase D: Subject+sender search failed", extra={
                                                        "email_id": msg_id, "error": str(e)
                                                    })

                                            # Strategy 3: If we have thread ID from Phase C context, use it
                                            # This is a fallback if Phase C ran but didn't clean up properly
                                            if not uids and original_uid:
                                                try:
                                                    # Try to find the original by UID in All Mail
                                                    # (UID might be different in All Mail vs Quarantine, but worth trying)
                                                    search_query = f'in:anywhere'
                                                    app_log.info("[Release] Phase D: Trying broad in:anywhere search", extra={
                                                        "email_id": msg_id
                                                    })
                                                    typ, data = imap.uid('SEARCH', None, 'X-GM-RAW', search_query)
                                                    # This is intentionally very broad and will need filtering
                                                    # We'll rely on the Message-ID verification in the next steps
                                                except Exception as e:
                                                    app_log.debug("[Release] Phase D: Broad search failed", extra={
                                                        "email_id": msg_id, "error": str(e)
                                                    })

                                            if uids:
                                                app_log.info("[Release] Phase D: SUCCESS - Broadened search found UIDs", extra={
                                                    "email_id": msg_id, "uids": uids, "hdr": hdr
                                                })
                                            else:
                                                app_log.info("[Release] Phase D: Broadened search exhausted, no results", extra={
                                                    "email_id": msg_id, "hdr": hdr
                                                })

                                        if not uids:
                                            app_log.info("[Gmail DEBUG] Header not found in All Mail, trying next",
                                                       extra={"email_id": msg_id, "hdr": hdr})
                                            continue

                                        # DEBUG: Log header searched and UIDs found for live testing validation
                                        app_log.info(f"[Gmail DEBUG] Found original in All Mail: header='{hdr}', UIDs={uids}",
                                                 extra={'email_id': msg_id})

                                        # Remove \Inbox label to prevent original from appearing in inbox view
                                        # This is the KEY fix for Gmail duplicates
                                        labels_cleared = 0
                                        moved_to_trash = 0
                                        for uid in uids:
                                            try:
                                                # Gmail-specific: Remove \Inbox and Quarantine labels
                                                # This prevents the original from showing up in Gmail's inbox view
                                                imap.uid('STORE', uid, '-X-GM-LABELS', r'(\Inbox Quarantine)')
                                                labels_cleared += 1

                                                # Optionally also trash the original (more aggressive cleanup)
                                                # This ensures it's fully removed, not just hidden from inbox
                                                if has_move:
                                                    # RFC 6851 MOVE: atomic operation
                                                    m_typ, _ = imap.uid('MOVE', uid, trash_box)
                                                    if m_typ == 'OK':
                                                        moved_to_trash += 1
                                                    else:
                                                        # MOVE failed, fall back to COPY+DELETE
                                                        imap.uid('COPY', uid, trash_box)
                                                        imap.uid('STORE', uid, '+FLAGS', r'(\Deleted)')
                                                        moved_to_trash += 1
                                                else:
                                                    # Traditional COPY+DELETE for servers without MOVE
                                                    imap.uid('COPY', uid, trash_box)
                                                    imap.uid('STORE', uid, '+FLAGS', r'(\Deleted)')
                                                    moved_to_trash += 1
                                            except Exception as uid_err:
                                                log.debug(f"[Gmail] Label removal/MOVE/COPY failed for UID {uid}: {uid_err}", exc_info=False)

                                        # EXPUNGE to physically remove from All Mail
                                        try:
                                            if has_uidplus:
                                                # RFC 4315: UID EXPUNGE - safer, only expunges messages with \Deleted in UID set
                                                imap.uid('EXPUNGE', ','.join(uids))
                                            else:
                                                # Traditional EXPUNGE - removes ALL \Deleted messages in mailbox
                                                imap.expunge()
                                        except Exception as exp_err:
                                            log.debug(f"[Gmail] EXPUNGE failed: {exp_err}", exc_info=False)

                                        if labels_cleared or moved_to_trash or uids:
                                            # All Mail cleanup SUCCESS
                                            app_log.debug("All Mail cleanup SUCCESS", extra={
                                                'email_id': msg_id,
                                                'account_id': row['account_id'],
                                                'message_id': hdr,
                                                'uids': uids,
                                                'labels_cleared': labels_cleared,
                                                'moved_to_trash': moved_to_trash,
                                                'mbox': all_mail_box,
                                                'trash': trash_box,
                                                'used_move': has_move,
                                                'used_uidplus': has_uidplus
                                            })
                                            break  # Success, move to next header if any
                                    except Exception as e:
                                        log.debug(f"[Gmail] All Mail cleanup failed for header: {e}", exc_info=False)
                                else:
                                    # Loop completed without break - nothing found in All Mail
                                    app_log.debug("All Mail cleanup: nothing to remove (likely already cleaned or not in All Mail)",
                                               extra={"email_id": msg_id, "headers_tried": header_candidates})
                        except Exception as e:
                            log.debug(f"[Gmail] All Mail purge block failed: {e}", exc_info=False)
            except Exception:
                pass

        except Exception as e:
            log.error(f"[interception::release] Failed to remove from quarantine: {e}", extra={'email_id': msg_id, 'uid': original_uid}, exc_info=True)

        # Post-condition verification: Check for duplicates in INBOX
        # IMPORTANT: Do this BEFORE logout() to avoid "illegal in state LOGOUT" error
        edited_message_id = msg.get('Message-ID')
        try:
            imap.select("INBOX", readonly=True)

            # Search using enhanced strategy (includes X-Google-Original-Message-ID)
            orig_uids = _robust_message_id_search(imap, "INBOX", original_message_id, is_gmail=is_gmail, tries=1, delay=0)

            if orig_uids:
                app_log.warning("[Verify] DUPLICATE DETECTED: Original still in INBOX after cleanup", extra={
                    "email_id": msg_id,
                    "orig_uids": orig_uids,
                    "original_message_id": original_message_id
                })
            else:
                app_log.info("[Verify] Original successfully removed from INBOX", extra={"email_id": msg_id})

            # Guard against null/empty edited Message-ID (some MTAs are creative)
            if edited_message_id:
                edited_uids = _robust_message_id_search(imap, "INBOX", edited_message_id, is_gmail=is_gmail, tries=1, delay=0)

                if not edited_uids:
                    app_log.warning("[Verify] Edited message not found in INBOX", extra={
                        "email_id": msg_id,
                        "edited_message_id": edited_message_id
                    })
                else:
                    app_log.info("[Verify] Edited message present in INBOX", extra={"email_id": msg_id, "edited_uids": edited_uids})
            else:
                app_log.debug("[Verify] Skipping edited message check (no Message-ID)", extra={"email_id": msg_id})
        except Exception as e:
            app_log.debug("[Verify] Post-condition check skipped (error)", extra={"err": str(e)})

        # All good; close IMAP connection (after verification!)
        try:
            imap.logout()
        except Exception:
            pass

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
    account_id = request.args.get('account_id', type=int)
    q = (request.args.get('q') or '').strip()
    limit = request.args.get('limit', type=int)
    if not limit or limit <= 0:
        limit = 200
    limit = max(10, min(limit, 500))
    conn = _db(); cur = conn.cursor(); params=[]; clauses=[]
    if status_filter:
        clauses.append("(interception_status = ? OR status = ?)"); params.extend([status_filter,status_filter])
    if account_id:
        clauses.append("account_id = ?"); params.append(account_id)
    if q:
        like=f"%{q}%"; clauses.append("(sender LIKE ? OR subject LIKE ?)"); params.extend([like,like])
    # Filter out SMTP self-check messages from inbox view
    clauses.append("sender != ?"); params.append('selfcheck@localhost')
    where = ('WHERE '+ ' AND '.join(clauses)) if clauses else ''
    rows = cur.execute(
        f"""
        SELECT id, account_id, sender, recipients, subject, interception_status, status, created_at, latency_ms, body_text, raw_path
        FROM email_messages
        {where}
        ORDER BY id DESC LIMIT ?
        """,
        (*params, limit)
    ).fetchall()
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


# ========== BATCH OPERATIONS FOR EMAIL MANAGEMENT ==========

@bp_interception.route('/api/emails/batch-discard', methods=['POST'])
@login_required
def api_batch_discard():
    """Batch discard emails (mark as DISCARDED, don't delete from database).
    
    Expects JSON body: { "email_ids": [1, 2, 3, ...] }
    Returns: { "success": true, "processed": 150, "failed": 0, "results": [...] }
    """
    try:
        data = request.get_json() or {}
        email_ids = data.get('email_ids', [])
        
        if not email_ids or not isinstance(email_ids, list):
            return jsonify({'success': False, 'error': 'email_ids array required'}), 400
        
        if len(email_ids) > 1000:
            return jsonify({'success': False, 'error': 'Maximum 1000 emails per batch'}), 400
        
        conn = _db()
        cur = conn.cursor()
        
        processed = 0
        failed = 0
        results = []
        
        # Batch update in single transaction for performance
        for email_id in email_ids:
            try:
                row = cur.execute(
                    "SELECT interception_status FROM email_messages WHERE id=?", 
                    (email_id,)
                ).fetchone()
                
                if not row:
                    failed += 1
                    results.append({'id': email_id, 'status': 'not_found'})
                    continue
                
                if row['interception_status'] == 'DISCARDED':
                    processed += 1
                    results.append({'id': email_id, 'status': 'already_discarded'})
                    continue
                
                cur.execute(
                    "UPDATE email_messages SET interception_status='DISCARDED', action_taken_at=datetime('now') WHERE id=?",
                    (email_id,)
                )
                processed += 1
                results.append({'id': email_id, 'status': 'discarded'})
                
            except Exception as e:
                failed += 1
                results.append({'id': email_id, 'status': 'error', 'error': str(e)})
                log.error(f"[batch-discard] Failed for email {email_id}: {e}")
        
        conn.commit()
        conn.close()
        
        # Audit log for batch operation
        try:
            from app.services.audit import log_action
            user_id = getattr(current_user, 'id', None)
            log_action('BATCH_DISCARD', user_id, None, f"Batch discarded {processed} emails (failed: {failed})")
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'processed': processed,
            'failed': failed,
            'total': len(email_ids),
            'results': results
        })
        
    except Exception as e:
        log.exception("[batch-discard] Unexpected error")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_interception.route('/api/emails/batch-delete', methods=['POST'])
@login_required
def api_batch_delete():
    """Permanently delete emails from database (hard delete).
    
    Expects JSON body: { "email_ids": [1, 2, 3, ...] }
    Returns: { "success": true, "deleted": 150, "failed": 0 }
    
    WARNING: This is permanent deletion. Cannot be undone.
    """
    try:
        data = request.get_json() or {}
        email_ids = data.get('email_ids', [])
        
        if not email_ids or not isinstance(email_ids, list):
            return jsonify({'success': False, 'error': 'email_ids array required'}), 400
        
        if len(email_ids) > 1000:
            return jsonify({'success': False, 'error': 'Maximum 1000 emails per batch'}), 400
        
        conn = _db()
        cur = conn.cursor()
        
        deleted = 0
        failed = 0
        
        # Use parameterized query with IN clause for batch delete
        placeholders = ','.join('?' * len(email_ids))
        
        try:
            cur.execute(
                f"DELETE FROM email_messages WHERE id IN ({placeholders})",
                email_ids
            )
            deleted = cur.rowcount
            conn.commit()
        except Exception as e:
            failed = len(email_ids)
            log.error(f"[batch-delete] Failed to delete emails: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()
        
        # Audit log for batch deletion
        try:
            from app.services.audit import log_action
            user_id = getattr(current_user, 'id', None)
            log_action('BATCH_DELETE', user_id, None, f"Permanently deleted {deleted} emails")
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'deleted': deleted,
            'failed': failed,
            'total': len(email_ids)
        })
        
    except Exception as e:
        log.exception("[batch-delete] Unexpected error")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp_interception.route('/api/emails/delete-all-discarded', methods=['DELETE', 'POST'])
@login_required
def api_delete_all_discarded():
    """Delete ALL emails with interception_status='DISCARDED' from database.
    
    Query params:
        - account_id (optional): Limit to specific account
        - confirm=yes (required): Safety confirmation
    
    Returns: { "success": true, "deleted": 523, "message": "..." }
    
    WARNING: This permanently deletes ALL discarded emails. Cannot be undone.
    """
    try:
        # Safety confirmation required
        confirm = request.args.get('confirm') or request.json.get('confirm') if request.json else None
        if confirm != 'yes':
            return jsonify({
                'success': False, 
                'error': 'Confirmation required. Pass confirm=yes'
            }), 400
        
        account_id = request.args.get('account_id', type=int)
        
        conn = _db()
        cur = conn.cursor()
        
        # Build delete query with optional account filter
        if account_id:
            cur.execute(
                "DELETE FROM email_messages WHERE interception_status='DISCARDED' AND account_id=?",
                (account_id,)
            )
        else:
            cur.execute("DELETE FROM email_messages WHERE interception_status='DISCARDED'")
        
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        
        # Audit log
        try:
            from app.services.audit import log_action
            user_id = getattr(current_user, 'id', None)
            scope = f"account_id={account_id}" if account_id else "all accounts"
            log_action('DELETE_ALL_DISCARDED', user_id, None, f"Deleted {deleted} discarded emails ({scope})")
        except Exception:
            pass
        
        message = f"Successfully deleted {deleted} discarded email(s)"
        if account_id:
            message += f" from account {account_id}"
        
        return jsonify({
            'success': True,
            'deleted': deleted,
            'message': message
        })
        
    except Exception as e:
        log.exception("[delete-all-discarded] Unexpected error")
        return jsonify({'success': False, 'error': str(e)}), 500
