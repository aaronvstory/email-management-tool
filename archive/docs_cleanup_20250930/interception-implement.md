# (Moved) See archive/root_docs_20250930/interception-implement.md

> NOTE: This document is superseded by `intercept-implementation.md`. Please hand the canonical step-by-step prompts to Claude Code from that file. This file remains for reference only.

NOTE: This file is superseded by `intercept-implementation.md` which contains the canonical, step-by-step plan Claude Code should follow (Prompt 0..6). Please use that file for the latest instructions. The content below remains for reference.

I’ll lay out a complete, staged implementation plan to auto‑use ManageSieve when available (Option A) and fall back to rapid IMAP hold‑and‑replace (Option B), with concrete code you can drop into the repo and a set of small, sequential prompts you can feed to Claude Code without overwhelming it.

## What we’ll deliver (checklist)

- Auto-detect ManageSieve support using only mailbox creds.
- Option A: ManageSieve deployer to hold inbound mail server-side in a Quarantine folder.
- Option B: Rapid IMAP watcher to immediately move new mail to Quarantine, then re-APPEND edited mail to Inbox.
- Minimal DB additions to track interception mode and Sieve status.
- Stepwise prompts for Claude Code: overview + 6 bite-size prompts with checks in between.
- Run/setup commands for Windows PowerShell (UV).

## Overview prompt for Claude Code

Paste this first to set context and goals.

Prompt 0: Overview and goals

- Goal: Implement inbound interception using only mailbox credentials. Prefer server-side hold via ManageSieve when available; else, perform rapid IMAP hold-and-replace. Do not change MX or provider routing.
- Deliverables:
  1. Sieve detection and manager (Option A)
  2. IMAP rapid watcher (Option B)
  3. Redelivery (IMAP APPEND of edited content)
  4. DB fields and health reporting
  5. Minimal wiring into the existing Flask app
- Constraints:
  - Only mailbox creds (IMAP/POP3/SMTP).
  - No admin/tenant/MX changes.
  - Handle Gmail/standard IMAP differences.
- Definition of done:
  - For providers that expose ManageSieve, new messages land in Quarantine (server moves them) and Inbox stays empty until approval.
  - For others, the watcher moves new mail to Quarantine within ~200 ms median.
  - Edited content is appended to Inbox, original retained in Quarantine for audit.

If this is clear, say “OK” and wait for Step 1.

## Step-by-step implementation prompts (each is small and testable)

Use these in order; each prompt includes success checks.

### Prompt 1: Dependencies and DB migrations

Objective: Add lightweight libs and DB columns.

- Add dependencies (preferred):
  - imapclient (robust IMAP with IDLE and MOVE)
  - backoff (reconnect logic)
  - dnspython (optional, SRV discovery for ManageSieve)
- Add DB columns to `email_accounts` for interception mode and sieve status.

Ask Claude Code to add these files and lines:

```powershell
# Install packages (dev machine)
uv pip install imapclient backoff dnspython
```

```python
import sqlite3

DB_PATH = 'email_manager.db'

def up():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(email_accounts)')
    cols = {row['name'] for row in cur.fetchall()}

    def maybe(sql):
        cur.execute(sql)

    if 'interception_mode' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN interception_mode TEXT DEFAULT 'unknown'")
    if 'sieve_status' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN sieve_status TEXT DEFAULT 'inactive'")
    if 'sieve_endpoint' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN sieve_endpoint TEXT")
    if 'last_probe_at' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_probe_at TEXT")
    if 'last_interception_ok_at' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_interception_ok_at TEXT")
    if 'last_error' not in cols:
        maybe("ALTER TABLE email_accounts ADD COLUMN last_error TEXT")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    up()
```

Success checks:

- Migration runs without error.
- Columns appear in `PRAGMA table_info(email_accounts)`.

### Prompt 2: Minimal ManageSieve client and detector

Objective: Implement a tiny ManageSieve client (STARTTLS + AUTH PLAIN + CAPABILITY + PUTSCRIPT + SETACTIVE), and an auto-detector that tries likely endpoints.

Add:

```python
import base64
import socket
import ssl
from typing import List, Tuple, Optional

class ManageSieveError(Exception):
    pass

class ManageSieveClient:
    def __init__(self, host: str, port: int = 4190, timeout: float = 15.0, require_starttls: bool = True):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.require_starttls = require_starttls
        self.sock: Optional[socket.socket] = None
        self.file = None
        self.caps = {}

    def _readline(self) -> str:
        line = self.file.readline()
        if not line:
            raise ManageSieveError("Connection closed")
        return line.decode('utf-8', errors='replace').rstrip('\r\n')

    def _writeline(self, s: str):
        self.sock.sendall((s + "\r\n").encode('utf-8'))

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.file = self.sock.makefile('rb')
        self._read_greeting()
        self.capability()
        if self.require_starttls and 'STARTTLS' in self.caps:
            self.starttls()
            self.capability()

    def _read_greeting(self):
        # Read until "OK" greeting line shows up
        # Greeting is a series of "IMPLEMENTATION"/"SASL"/"SIEVE" lines followed by "OK"
        while True:
            line = self._readline()
            if line.startswith('OK'):
                break
            # ignore other greeting lines

    def capability(self):
        self._writeline('CAPABILITY')
        caps = {}
        while True:
            line = self._readline()
            if line.startswith('OK'):
                break
            # Example: "SIEVE" "fileinto" "imap4flags"
            # Or: "SASL" "PLAIN" "LOGIN"
            parts = [p.strip('"') for p in line.split()]
            if not parts:
                continue
            key = parts[0].upper()
            vals = [p.strip('"') for p in parts[1:]]
            caps[key] = vals
        self.caps = caps
        return caps

    def starttls(self):
        self._writeline('STARTTLS')
        line = self._readline()
        if not line.startswith('OK'):
            raise ManageSieveError(f"STARTTLS refused: {line}")
        ctx = ssl.create_default_context()
        self.sock = ctx.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile('rb')

    def auth_plain(self, username: str, password: str):
        if 'SASL' in self.caps and 'PLAIN' not in [m.upper() for m in self.caps['SASL']]:
            raise ManageSieveError("Server does not support SASL PLAIN")
        self._writeline('AUTHENTICATE "PLAIN"')
        # Server sends a base64 challenge on its own line
        line = self._readline()
        if not line or line.upper().startswith('NO') or line.upper().startswith('BYE'):
            raise ManageSieveError(f"AUTH PLAIN not accepted: {line}")
        authzid = ''
        msg = (authzid + '\x00' + username + '\x00' + password).encode('utf-8')
        b64 = base64.b64encode(msg).decode('ascii')
        self._writeline('{' + str(len(b64)) + '+}')
        self._writeline(b64)
        resp = self._readline()
        if not resp.startswith('OK'):
            raise ManageSieveError(f"AUTH failed: {resp}")

    def listscripts(self) -> Tuple[Optional[str], List[str]]:
        self._writeline('LISTSCRIPTS')
        scripts = []
        active = None
        while True:
            line = self._readline()
            if line.startswith('OK'):
                break
            # "SCRIPT" "name" or "ACTIVE" "name"
            parts = [p.strip('"') for p in line.split()]
            if not parts:
                continue
            if parts[0].upper() == 'ACTIVE':
                active = parts[1]
                scripts.append(parts[1])
            elif parts[0].upper() == 'SCRIPT':
                scripts.append(parts[1])
        return active, scripts

    def putscript(self, name: str, content: str):
        payload = content.encode('utf-8')
        self._writeline(f'PUTSCRIPT "{name}" {{{len(payload)}+}}')
        # Literal follows on next line(s)
        self.sock.sendall(payload + b"\r\n")
        resp = self._readline()
        if not resp.startswith('OK'):
            raise ManageSieveError(f"PUTSCRIPT failed: {resp}")

    def setactive(self, name: str):
        self._writeline(f'SETACTIVE "{name}"')
        resp = self._readline()
        if not resp.startswith('OK'):
            raise ManageSieveError(f"SETACTIVE failed: {resp}")

    def getscript(self, name: str) -> str:
        self._writeline(f'GETSCRIPT "{name}"')
        # Server returns a literal size line: {N+}
        line = self._readline()
        if line.upper().startswith('NO'):
            raise ManageSieveError(f"GETSCRIPT failed: {line}")
        if not line.startswith('{') or '}' not in line:
            raise ManageSieveError(f"Unexpected GETSCRIPT literal: {line}")
        size = int(line[1:line.index('}')].rstrip('+'))
        data = self.file.read(size)
        # Consume trailing OK
        tail = self._readline()
        if not tail.startswith('OK'):
            raise ManageSieveError(f"GETSCRIPT tail failed: {tail}")
        return data.decode('utf-8', errors='replace')

    def close(self):
        try:
            if self.file: self.file.close()
            if self.sock: self.sock.close()
        finally:
            self.file = None
            self.sock = None
```

```python
from typing import Optional, List, Tuple
import socket

try:
    import dns.resolver  # optional
except Exception:
    dns = None

COMMON_SIEVE_PORT = 4190

def candidate_endpoints(email_domain: str, imap_host: str) -> List[Tuple[str, int]]:
    hosts = []
    # SRV discovery if dnspython available
    if dns:
        try:
            for name in [f"_sieve._tcp.{email_domain}", f"_sieve._tcp.{imap_host.split('.',1)[-1]}"]:
                for r in dns.resolver.resolve(name, 'SRV'):
                    hosts.append((str(r.target).rstrip('.'), int(r.port)))
        except Exception:
            pass
    # Direct guesses
    candidates = [
        (imap_host, COMMON_SIEVE_PORT),
        (f"sieve.{email_domain}", COMMON_SIEVE_PORT),
        (f"managesieve.{email_domain}", COMMON_SIEVE_PORT),
        (f"mail.{email_domain}", COMMON_SIEVE_PORT),
    ]
    # Deduplicate, preserve order
    seen = set()
    for h in candidates + hosts:
        if h not in seen:
            seen.add(h)
    return list(seen)

def tcp_probe(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False
```

```python
from typing import Optional, Tuple
from app.services.sieve_client import ManageSieveClient, ManageSieveError
from app.services.sieve_detector import candidate_endpoints, tcp_probe
from imapclient import IMAPClient

HOLD_SCRIPT_NAME = "hold_all"
HOLD_SCRIPT = '''require ["fileinto"];
fileinto "Quarantine";
stop;
'''

class SieveManager:
    def __init__(self, email_domain: str, imap_host: str, username: str, password: str, use_starttls: bool = True):
        self.email_domain = email_domain
        self.imap_host = imap_host
        self.username = username
        self.password = password
        self.use_starttls = use_starttls

    def ensure_quarantine_folder(self) -> bool:
        with IMAPClient(self.imap_host, ssl=True) as imap:
            imap.login(self.username, self.password)
            folders = [f.decode() if isinstance(f, bytes) else f for f in imap.list_folders()]
            names = {f[-1] for f in folders}
            if 'Quarantine' not in names:
                imap.create_folder('Quarantine')
            return True

    def try_activate_hold(self) -> Optional[Tuple[str, str]]:
        """
        Returns (endpoint_host, status) if success, else None.
        """
        self.ensure_quarantine_folder()
        for host, port in candidate_endpoints(self.email_domain, self.imap_host):
            if not tcp_probe(host, port):
                continue
            try:
                client = ManageSieveClient(host, port, require_starttls=True)
                client.connect()
                client.auth_plain(self.username, self.password)
                caps = client.caps.get('SIEVE', [])
                if 'fileinto' not in [c.lower() for c in caps]:
                    client.close()
                    continue
                # Install script
                client.putscript(HOLD_SCRIPT_NAME, HOLD_SCRIPT)
                client.setactive(HOLD_SCRIPT_NAME)
                client.close()
                return (f"{host}:{port}", "active")
            except ManageSieveError:
                continue
            except Exception:
                continue
        return None
```

Success checks:

- Static import is valid.
- Detector returns endpoints for a sample domain and IMAP host.
- Manager compiles; no socket calls are made yet in tests.

### Prompt 3: IMAP rapid watcher (Option B) with IDLE and atomic MOVE

Objective: Implement a per-account watcher that:

- Maintains a persistent IMAP connection to INBOX.
- On new message, immediately MOVE to Quarantine (atomic when supported), else COPY+DELETE+EXPUNGE fallback.
- Records metadata for the app to display.

Add:

```python
import time
import threading
from typing import Optional, List, Dict, Any
from imapclient import IMAPClient, exceptions as imap_exc

# Optional: add backoff for reconnects
try:
    import backoff
except Exception:
    backoff = None

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

    def _connect(self) -> IMAPClient:
        c = IMAPClient(self.imap_host, ssl=True)
        c.login(self.username, self.password)
        # Ensure Quarantine exists
        try:
            c.select_folder(self.quarantine)
        except imap_exc.IMAPClientError:
            c.create_folder(self.quarantine)
        return c

    def _move_atomic(self, c: IMAPClient, uids: List[int]):
        try:
            # UID MOVE if supported
            c.move(uids, self.quarantine)
        except imap_exc.IMAPClientError:
            # Fallback: COPY + DELETE + EXPUNGE
            c.copy(uids, self.quarantine)
            c.add_flags(uids, [b'\\Deleted'])
            c.expunge()

    def run(self):
        while not self._stop.is_set():
            try:
                with self._connect() as c:
                    c.select_folder("INBOX")
                    # Track last seen UID for delta
                    status = c.folder_status("INBOX", [b'UIDNEXT'])
                    last_uidnext = status[b'UIDNEXT']
                    while not self._stop.is_set():
                        # IDLE wait
                        with c.idle():
                            # Wait up to 60s for changes
                            responses = c.idle_check(timeout=60)
                        # On exit from IDLE, check for new messages
                        status2 = c.folder_status("INBOX", [b'UIDNEXT'])
                        uidnext2 = status2[b'UIDNEXT']
                        if uidnext2 > last_uidnext:
                            new_uid_first = last_uidnext
                            new_uids = c.search([u'UID', f'{new_uid_first}:{uidnext2 - 1}'])
                            if new_uids:
                                # Rapidly move new messages to Quarantine
                                self._move_atomic(c, new_uids)
                            last_uidnext = uidnext2
            except Exception:
                # brief backoff
                time.sleep(2.0)
                continue
```

Success checks:

- Module imports correctly.
- The thread class can be instantiated.
- No runtime yet; just ensure no syntax errors.

### Prompt 4: Redelivery (APPEND) and simple approval hook

Objective: Provide functions to append edited messages into Inbox and a minimal route to trigger it (you can wire to your existing approval flow).

Add:

```python
from imapclient import IMAPClient
from email.message import EmailMessage
from typing import Optional
import email.utils
import time

def append_edited_to_inbox(imap_host: str, username: str, password: str, mime_bytes: bytes, internaldate: Optional[float] = None):
    """
    Appends the edited message to INBOX as unseen.
    internaldate: epoch seconds to preserve original Date ordering (optional).
    """
    flags = []
    when = internaldate if internaldate else time.time()
    with IMAPClient(imap_host, ssl=True) as c:
        c.login(username, password)
        c.append('INBOX', mime_bytes, flags=flags, msg_time=when)
```

Optionally show how to call this from your existing approval route (do not overwrite complete file, just the conceptual snippet):

```python
# ...existing code...
from flask import request, jsonify
from app.services.mail_redeliver import append_edited_to_inbox

@app.post('/email/<int:email_id>/approve-and-append')
def approve_and_append(email_id):
    """
    Conceptual: fetch the edited MIME from DB/UI, then APPEND to target account's INBOX.
    """
    # 1) Load email/account info and edited MIME from your DB
    # edited_mime_bytes = ...
    # account = ...
    # 2) Append to INBOX
    # append_edited_to_inbox(account.imap_host, account.username, account.password, edited_mime_bytes, internaldate=None)
    return jsonify({"ok": True})
# ...existing code...
```

Success checks:

- Module imports.
- No syntax errors.

### Prompt 5: Auto mode selection and wiring

Objective: Given an account (email address, imap host, username, password), try ManageSieve and if successful, mark interception_mode = sieve; otherwise, start the IMAP rapid watcher.

Add:

```python
from typing import Optional
from app.services.sieve_manager import SieveManager
from app.services.imap_watcher import IMAPRapidInterceptor
import threading
import time
import sqlite3

DB_PATH = 'email_manager.db'

def set_account_fields(account_id: int, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    updates = ','.join([f"{k}=?" for k in kwargs.keys()])
    params = list(kwargs.values()) + [account_id]
    cur.execute(f"UPDATE email_accounts SET {updates} WHERE id=?", params)
    conn.commit()
    conn.close()

def bootstrap_account(account_id: int, email_address: str, imap_host: str, username: str, password: str):
    domain = email_address.split('@')[-1].lower()
    mgr = SieveManager(domain, imap_host, username, password)
    result = mgr.try_activate_hold()
    if result:
        endpoint, status = result
        set_account_fields(
            account_id,
            interception_mode='sieve',
            sieve_status=status,
            sieve_endpoint=endpoint,
            last_probe_at=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        # In sieve mode, you may still run a light watcher to monitor Quarantine (optional)
        return 'sieve'
    else:
        set_account_fields(
            account_id,
            interception_mode='imap',
            sieve_status='inactive',
            last_probe_at=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        # Start rapid watcher
        t = IMAPRapidInterceptor(imap_host, username, password)
        t.start()
        return 'imap'
```

You can call `bootstrap_account` when accounts are activated (e.g., from an admin action or at app startup).

Success checks:

- Imports clean.
- You can call `bootstrap_account` with sample data and it returns either 'sieve' or 'imap' (without actually connecting if not reachable here).

### Prompt 6: Operational scripts and how to run locally

Objective: Add a small runner for manual test and document the commands.

Add:

```python
# Quick manual runner (dev). Reads a single account from DB and bootstraps interception.
import sqlite3
from app.services.interception_bootstrap import bootstrap_account

DB_PATH = 'email_manager.db'

def first_active_account():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM email_accounts WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
    conn.close()
    return row

if __name__ == "__main__":
    acc = first_active_account()
    if not acc:
        print("No active account found.")
    else:
        mode = bootstrap_account(acc['id'], acc['email_address'], acc['imap_host'], acc['imap_username'], acc['imap_password'])
        print(f"Interception bootstrapped in mode: {mode}")
        # Keep process alive if IMAP watcher thread is running
        if mode == 'imap':
            import time
            while True:
                time.sleep(5)
```

Run (Windows PowerShell):

```powershell
# 1) Run DB migration
uv python scripts/migrations/20250914_add_interception_fields.py

# 2) Install deps
uv pip install imapclient backoff dnspython

# 3) Start the interceptor runner (dev)
uv python scripts/run_interceptors.py
```

Success checks:

- For servers with ManageSieve, expect mode = sieve (and messages auto-filed to Quarantine).
- For others, mode = imap and the watcher thread runs.

## How it works (quick technical notes)

- Option A (ManageSieve): We detect an endpoint (SRV or common hostnames), use the same mailbox creds to authenticate, upload a simple Sieve script that files all new mail into “Quarantine”, and set it active. Inbox remains empty until you re-APPEND the edited message.
- Option B (Rapid IMAP): We maintain a persistent IMAP IDLE connection to INBOX. On new mail, we immediately MOVE it to Quarantine (or COPY+DELETE if MOVE unsupported). Then your reviewers edit the content; we APPEND the edited message to INBOX so it appears as the “real” message. The original remains in Quarantine for audit.

Gmail specifics:

- MOVE becomes removing the Inbox label and adding Quarantine; `imapclient` handles MOVE where supported. If running against Gmail, the behavior maps to label operations internally.

Limits to be aware of:

- Rapid IMAP is best-effort “pre-read”—push notifications may still briefly appear, and server-side forwarding/auto-replies could fire before we move the message. Sieve mode avoids this if available.

## Small adjacent improvements (optional)

- Add metrics: time from IDLE wake to MOVE completion to estimate “exposure window”.
- Add a “Test interception” button per account (send a probe message, verify it lands in Quarantine).
- Add a “Restore Sieve” action to remove our script and reinstate prior user script, if any.

## Quality gates

- Build/lint: Python files import clean; no syntax errors.
- Minimal smoke: Run the interceptor runner; verify that no exceptions are thrown when the server is reachable.
- Requirements coverage:
  - Auto-detect Sieve and prefer Option A: Included.
  - Fallback to Option B when Sieve unavailable: Included.
  - Inbound-only with mailbox creds: Satisfied.
  - Editing and redelivery via APPEND: Included.

If you’d like, I can further adapt the watcher to also monitor the Quarantine folder and populate your existing templates with a new “Pending inbound” view, but this gives Claude Code a clear, staged track to get interception working now.
