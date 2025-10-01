from typing import Optional, Tuple
from imapclient import IMAPClient, exceptions as imap_exc
from .sieve_client import ManageSieveClient, ManageSieveError
from .sieve_detector import candidate_endpoints, tcp_probe

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
            try:
                imap.select_folder('Quarantine')
            except imap_exc.IMAPClientError:
                imap.create_folder('Quarantine')
        return True

    def try_activate_hold(self) -> Optional[Tuple[str, str]]:
        """
        Returns (endpoint_host, status) if success, else None.
        """
        self.ensure_quarantine_folder()
        endpoints = candidate_endpoints(self.email_domain, self.imap_host)
        for host, port in endpoints:
            if not tcp_probe(host, port):
                continue
            try:
                client = ManageSieveClient(host, port, require_starttls=True)
                client.connect()
                client.auth_plain(self.username, self.password)
                caps = [c.lower() for c in client.caps.get('SIEVE', [])]
                if 'fileinto' not in caps:
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
