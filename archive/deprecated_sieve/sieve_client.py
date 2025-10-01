import base64
import socket
import ssl
from typing import List, Tuple, Optional


class ManageSieveError(Exception):
    pass


class ManageSieveClient:
    """Minimal ManageSieve client with STARTTLS, AUTH PLAIN, CAPABILITY, PUTSCRIPT, SETACTIVE, GETSCRIPT."""

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
        while True:
            line = self._readline()
            if line.startswith('OK'):
                break

    def capability(self):
        self._writeline('CAPABILITY')
        caps = {}
        while True:
            line = self._readline()
            if line.startswith('OK'):
                break
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
        line = self._readline()
        if line.upper().startswith('NO'):
            raise ManageSieveError(f"GETSCRIPT failed: {line}")
        if not line.startswith('{') or '}' not in line:
            raise ManageSieveError(f"Unexpected GETSCRIPT literal: {line}")
        size = int(line[1:line.index('}')].rstrip('+'))
        data = self.file.read(size)
        tail = self._readline()
        if not tail.startswith('OK'):
            raise ManageSieveError(f"GETSCRIPT tail failed: {tail}")
        return data.decode('utf-8', errors='replace')

    def close(self):
        try:
            if self.file:
                self.file.close()
            if self.sock:
                self.sock.close()
        finally:
            self.file = None
            self.sock = None
