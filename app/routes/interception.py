"""Interception & Inbox Blueprint (Phase 2 Migration).

Contains: healthz, interception dashboard APIs, inbox API, edit, release, discard.
Diff and attachment scrubbing supported.
"""
import os
import time
import statistics
from datetime import datetime
import sqlite3
from typing import Dict, Any
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from email.parser import BytesParser
from email.policy import default as default_policy
import difflib
import imaplib, ssl

from app.utils.db import get_db, DB_PATH
from app.utils.crypto import decrypt_credential, encrypt_credential

bp_interception = Blueprint('interception_bp', __name__)

def _db():
    """Get database connection with Row factory"""
    return get_db()

WORKER_HEARTBEATS = {}
_HEALTH_CACHE: Dict[str, Any] = {'ts': 0.0, 'payload': None}

@bp_interception.route('/healthz')
def healthz():
    now = time.time()
    if _HEALTH_CACHE['payload'] and now - _HEALTH_CACHE['ts'] < 5:
        cached = dict(_HEALTH_CACHE['payload']); cached['cached'] = True
        return jsonify(cached), 200 if cached.get('ok') else 503
    info = {'ok': True,'db': None,'held_count':0,'released_24h':0,'median_latency_ms':None,'workers':[], 'timestamp': datetime.utcnow().isoformat()+'Z'}
    try:
        conn = _db(); cur = conn.cursor()
        info['held_count'] = cur.execute("SELECT COUNT(*) FROM email_messages WHERE direction='inbound' AND interception_status='HELD'").fetchone()[0]
        info['released_24h'] = cur.execute("SELECT COUNT(*) FROM email_messages WHERE direction='inbound' AND interception_status='RELEASED' AND created_at >= datetime('now','-1 day')").fetchone()[0]
        lat_rows = cur.execute("SELECT latency_ms FROM email_messages WHERE latency_ms IS NOT NULL ORDER BY id DESC LIMIT 200").fetchall()
        latencies = [r['latency_ms'] for r in lat_rows if r['latency_ms'] is not None]
        if latencies:
            info['median_latency_ms'] = int(statistics.median(latencies))
        now_ts = time.time(); info['workers'] = [{ 'worker': wid,'last_heartbeat_sec': round(now_ts - hb,2),'status':'stale' if (now_ts-hb)>60 else 'ok'} for wid,hb in WORKER_HEARTBEATS.items()]
        conn.close(); info['db'] = 'ok'
    except Exception as e:
        info['ok'] = False; info['error'] = str(e)
    _HEALTH_CACHE['ts'] = now; _HEALTH_CACHE['payload'] = info
    return jsonify(info), 200 if info.get('ok') else 503

@bp_interception.route('/interception')
@login_required
def interception_dashboard():
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
    return jsonify({'messages':[dict(r) for r in rows], 'stats':{'held':len(rows),'released24h':released24,'median_latency_ms':median_latency,'accounts_active':accounts_active}})

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
@login_required
def api_interception_release(msg_id:int):
    payload = request.get_json(silent=True) or {}
    edited_subject = payload.get('edited_subject'); edited_body = payload.get('edited_body')
    target_folder = payload.get('target_folder','INBOX')
    strip_attachments = bool(payload.get('strip_attachments'))
    conn = _db(); cur = conn.cursor()
    row = cur.execute("""
        SELECT em.*, ea.imap_host, ea.imap_port, ea.imap_username, ea.imap_password, ea.imap_use_ssl
        FROM email_messages em JOIN email_accounts ea ON em.account_id = ea.id
        WHERE em.id=? AND em.direction='inbound' AND em.interception_status='HELD'
    """, (msg_id,)).fetchone()
    if not row:
        conn.close(); return jsonify({'ok':False,'reason':'not-held'}), 409
    raw_path = row['raw_path']
    if not raw_path or not os.path.exists(raw_path):
        conn.close(); return jsonify({'ok':False,'reason':'raw-missing'}), 500
    with open(raw_path,'rb') as f: original_bytes = f.read()
    msg = BytesParser(policy=default_policy).parsebytes(original_bytes)
    if edited_subject:
        msg.replace_header('Subject', edited_subject) if msg['Subject'] else msg.add_header('Subject', edited_subject)
    if edited_body:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type()=='text/plain':
                    part.set_content(edited_body); break
        else:
            from email.message import EmailMessage
            new_msg = EmailMessage();
            for k,v in msg.items():
                if k.lower() != 'content-type': new_msg[k] = v
            new_msg.set_content(edited_body); msg = new_msg
    removed = []
    if strip_attachments and msg.is_multipart():
        from email.message import EmailMessage
        new_container = EmailMessage()
        for k,v in msg.items(): new_container[k] = v
        for part in msg.walk():
            if part.is_multipart(): continue
            disp = (part.get_content_disposition() or '').lower()
            if disp == 'attachment':
                removed.append(part.get_filename() or 'attachment.bin'); continue
            ctype = part.get_content_type()
            if ctype == 'text/plain': new_container.set_content(part.get_content())
            elif ctype == 'text/html':
                try: new_container.add_alternative(part.get_content(), subtype='html')
                except Exception: pass
        if removed:
            notice = '\n\n[Attachments removed: ' + ', '.join(removed) + ']'
            try:
                body = new_container.get_body(preferencelist=('plain',))
                if body:
                    new_container.set_content(body.get_content()+notice)
            except Exception: pass
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
        internaldate = row['original_internaldate'] or datetime.utcnow().strftime('%d-%b-%Y %H:%M:%S +0000')
        imap.append(target_folder, '', internaldate, msg.as_bytes()); imap.logout()
    except Exception as e:
        conn.close(); return jsonify({'ok':False,'reason':'append-failed','error':str(e)}), 500
    cur.execute("UPDATE email_messages SET interception_status='RELEASED', action_taken_at=datetime('now'), edited_message_id=? WHERE id=?", (msg.get('Message-ID'), msg_id))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'released_to':target_folder,'attachments_removed':removed})

@bp_interception.route('/api/interception/discard/<int:msg_id>', methods=['POST'])
@login_required
def api_interception_discard(msg_id:int):
    conn = _db(); cur = conn.cursor()
    cur.execute("UPDATE email_messages SET interception_status='DISCARDED', action_taken_at=datetime('now') WHERE id=? AND interception_status='HELD'", (msg_id,))
    changed = cur.rowcount; conn.commit(); conn.close()
    if changed == 0: return jsonify({'ok':False,'reason':'not-held'}), 409
    return jsonify({'ok':True})

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
    conn.commit(); conn.close(); return jsonify({'ok':True,'updated_fields':[f.split('=')[0].strip() for f in fields]})
