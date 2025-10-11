"""
IMAP Helper Functions

Extracted from simple_app.py to eliminate circular dependencies in blueprints.
Provides IMAP connection, quarantine management, and message moving utilities.
"""

import imaplib
from typing import Tuple, Optional

from app.utils.crypto import decrypt_credential


def _imap_connect_account(account_row) -> Tuple[imaplib.IMAP4, bool]:
    """Connect to IMAP account and return (imap_obj, supports_move)"""
    host = account_row['imap_host']
    port = int(account_row['imap_port'] or 993)
    username = account_row['imap_username']
    password = decrypt_credential(account_row['imap_password'])
    if not (host and username and password):
        raise RuntimeError("Missing IMAP credentials")
    if port == 993:
        imap_obj = imaplib.IMAP4_SSL(host, port)
    else:
        imap_obj = imaplib.IMAP4(host, port)
        try:
            imap_obj.starttls()
        except Exception:
            pass
    pwd: str = password  # type: ignore[assignment]
    imap_obj.login(username, pwd)
    try:
        typ, caps = imap_obj.capability()
        supports_move = any(b'MOVE' in c.upper() for c in caps) if isinstance(caps, list) else False
    except Exception:
        supports_move = False
    return imap_obj, supports_move


def _ensure_quarantine(imap_obj: imaplib.IMAP4, folder_name: str = "Quarantine") -> None:
    """Ensure quarantine folder exists"""
    try:
        imap_obj.create(folder_name)
    except Exception:
        pass


def _move_uid_to_quarantine(imap_obj: imaplib.IMAP4, uid: str, quarantine: str = "Quarantine") -> bool:
    """Move message to quarantine using MOVE or COPY+DELETE fallback"""
    _ensure_quarantine(imap_obj, quarantine)
    # Try native MOVE
    try:
        typ, _ = imap_obj.uid('MOVE', uid, quarantine)
        if typ == 'OK':
            return True
    except Exception:
        pass
    # Fallback: COPY + delete
    try:
        typ, _ = imap_obj.uid('COPY', uid, quarantine)
        if typ == 'OK':
            imap_obj.uid('STORE', uid, '+FLAGS', r'(\Deleted)')
            imap_obj.expunge()
            return True
    except Exception:
        pass
    return False