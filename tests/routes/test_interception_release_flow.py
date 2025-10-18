from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default as default_policy
from types import SimpleNamespace

from app.routes import interception as route
from app.utils.crypto import encrypt_credential
from app.utils.db import get_db
from tests.routes.test_interception_additional import _login


class ReleaseIMAP:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.current_folder = None
        self.appended = False
        self.mailboxes = {
            "INBOX": {},
            "Quarantine": {}
        }
        self.deleted_uids = []

    def preload(self, folder, uid, message_id):
        self.mailboxes.setdefault(folder, {})[uid] = message_id

    def login(self, username, password):
        self.username = username
        self.password = password

    def select(self, mailbox):
        self.current_folder = mailbox
        return "OK", [b"1"]

    def search(self, charset, criterion, header, value):
        if self.current_folder not in self.mailboxes:
            return "NO", [b""]
        matches = [uid for uid, msgid in self.mailboxes[self.current_folder].items() if msgid == value]
        result = b" ".join(str(uid).encode() for uid in matches) if matches else b""
        return "OK", [result]

    def append(self, folder, flags, date_time, message_bytes):
        self.appended = True
        msg = BytesParser(policy=default_policy).parsebytes(message_bytes)
        mid = (msg["Message-ID"] or "").strip()
        mailbox = self.mailboxes.setdefault(folder, {})
        new_uid = max(mailbox.keys() or [400]) + 1
        mailbox[new_uid] = mid
        return "OK", [b"APPEND completed"]

    def uid(self, command, *args):
        if command == 'SEARCH':
            _, criterion, data = args[0], args[1], args[2]
            if criterion == 'HEADER' and self.current_folder in self.mailboxes:
                value = args[3]
                matches = [uid for uid, msgid in self.mailboxes[self.current_folder].items() if msgid == value]
                return "OK", [b" ".join(str(uid).encode() for uid in matches) if matches else b""]
            if criterion == 'UID':
                value = int(args[2])
                matches = [value] if value in self.mailboxes.get(self.current_folder, {}) else []
                return "OK", [b" ".join(str(uid).encode() for uid in matches) if matches else b""]
        if command == 'STORE':
            uid = int(args[0])
            if self.current_folder in self.mailboxes and uid in self.mailboxes[self.current_folder]:
                self.mailboxes[self.current_folder].pop(uid, None)
                self.deleted_uids.append(uid)
            return "OK", [b"OK"]
        return "OK", [b""]

    def expunge(self):
        return "OK", [b"1"]

    def logout(self):
        return "BYE", []


def _prepare_release_fixture(raw_path, account_id=1, email_id=1):
    conn = get_db()
    conn.execute("DELETE FROM email_messages")
    conn.execute("DELETE FROM email_accounts")
    conn.execute(
        """
        INSERT INTO email_accounts
        (id, account_name, email_address, imap_host, imap_port, imap_username, imap_password, imap_use_ssl, is_active)
        VALUES (?, 'Release Account', 'release{0}@example.com', 'imap.release.test', 993, 'release_user', ?, 1, 1)
        """.format(account_id),
        (account_id, encrypt_credential("release-secret")),
    )
    conn.execute(
        """
        INSERT INTO email_messages
        (id, account_id, interception_status, status, subject, body_text, raw_path, direction, original_uid, message_id)
        VALUES (?, ?, 'HELD', 'PENDING', 'Orig Subject', 'Stored body', ?, 'inbound', 321, '<release-test@example.com>')
        """,
        (email_id, account_id, str(raw_path)),
    )
    conn.commit()


def test_release_endpoint_strips_attachments(monkeypatch, client, tmp_path):
    _login(client)

    msg = EmailMessage()
    msg["Subject"] = "Orig Subject"
    msg.set_content("Plain body")
    msg.add_alternative("<p>HTML body</p>", subtype="html")
    msg.add_attachment(b"binary-data", maintype="application", subtype="pdf", filename="report.pdf")

    raw_file = tmp_path / "release.eml"
    raw_file.write_bytes(msg.as_bytes())

    _prepare_release_fixture(raw_file, account_id=42, email_id=77)

    fake_imap = ReleaseIMAP("imap.release.test", 993)
    fake_imap.preload("Quarantine", 321, "<release-test@example.com>")
    monkeypatch.setattr(route, "imaplib", SimpleNamespace(IMAP4_SSL=lambda *args, **kwargs: fake_imap, Time2Internaldate=route.imaplib.Time2Internaldate, IMAP4=route.imaplib.IMAP4))
    monkeypatch.setattr(route, "_ensure_quarantine", lambda imap_obj, folder: folder)

    response = client.post(
        "/api/interception/release/77",
        json={"target_folder": "INBOX", "strip_attachments": True},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["attachments_removed"] == ["report.pdf"]
    row = get_db().execute("SELECT interception_status, status FROM email_messages WHERE id=77").fetchone()
    assert row["interception_status"] == "RELEASED"
    assert fake_imap.mailboxes["Quarantine"] == {}
    inbox_mids = list(fake_imap.mailboxes["INBOX"].values())
    assert len(inbox_mids) == 1
    assert inbox_mids[0] != "<release-test@example.com>"


def test_release_endpoint_uses_raw_content(monkeypatch, client):
    _login(client)

    msg = EmailMessage()
    msg["Subject"] = "Raw Content Subject"
    msg.set_content("Body for raw content")
    raw_payload = msg.as_string()

    conn = get_db()
    conn.execute("DELETE FROM email_messages")
    conn.execute("DELETE FROM email_accounts")
    conn.execute(
        """
        INSERT INTO email_accounts
        (id, account_name, email_address, imap_host, imap_port, imap_username, imap_password, imap_use_ssl, is_active)
        VALUES (55, 'Content Account', 'content55@example.com', 'imap.content.test', 993, 'content_user', ?, 1, 1)
        """,
        (encrypt_credential("content-secret"),),
    )
    conn.execute(
        """
        INSERT INTO email_messages
        (id, account_id, interception_status, status, subject, body_text, raw_path, raw_content, direction, original_uid, message_id)
        VALUES (88, 55, 'HELD', 'PENDING', 'Raw Content Subject', 'Stored', NULL, ?, 'inbound', 111, '<raw-content@example.com>')
        """,
        (raw_payload,),
    )
    conn.commit()

    fake_imap = ReleaseIMAP("imap.content.test", 993)
    fake_imap.preload("Quarantine", 111, "<raw-content@example.com>")
    monkeypatch.setattr(route, "imaplib", SimpleNamespace(IMAP4_SSL=lambda *args, **kwargs: fake_imap, Time2Internaldate=route.imaplib.Time2Internaldate, IMAP4=route.imaplib.IMAP4))
    monkeypatch.setattr(route, "_ensure_quarantine", lambda imap_obj, folder: folder)

    response = client.post(
        "/api/interception/release/88",
        json={"target_folder": "INBOX"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    row = get_db().execute("SELECT interception_status FROM email_messages WHERE id=88").fetchone()
    assert row["interception_status"] == "RELEASED"


def test_release_quarantine_cleanup_handles_failures(monkeypatch, client):
    _login(client)

    class QuarantineIMAP(ReleaseIMAP):
        def select(self, mailbox):
            if mailbox == "INBOX":
                return super().select(mailbox)
            if mailbox == "INBOX/Quarantine":
                raise RuntimeError("mailbox unavailable")
            if mailbox == "INBOX.Quarantine":
                return "NO", []
            return super().select(mailbox)

    msg = EmailMessage()
    msg["Subject"] = "Cleanup Subject"
    msg.set_content("Body")

    conn = get_db()
    conn.execute("DELETE FROM email_messages")
    conn.execute("DELETE FROM email_accounts")
    conn.execute(
        """
        INSERT INTO email_accounts
        (id, account_name, email_address, imap_host, imap_port, imap_username, imap_password, imap_use_ssl, is_active)
        VALUES (66, 'Cleanup Account', 'cleanup66@example.com', 'imap.cleanup.test', 993, 'cleanup_user', ?, 1, 1)
        """,
        (encrypt_credential("cleanup-secret"),),
    )
    conn.execute(
        """
        INSERT INTO email_messages
        (id, account_id, interception_status, status, subject, body_text, raw_content, direction, original_uid, message_id)
        VALUES (99, 66, 'HELD', 'PENDING', 'Cleanup Subject', 'Body', ?, 'inbound', 222, '<cleanup@example.com>')
        """,
        (msg.as_string(),),
    )
    conn.commit()

    fake_imap = QuarantineIMAP("imap.cleanup.test", 993)
    fake_imap.preload("Quarantine", 222, "<cleanup@example.com>")
    monkeypatch.setattr(route, "imaplib", SimpleNamespace(IMAP4_SSL=lambda *args, **kwargs: fake_imap, Time2Internaldate=route.imaplib.Time2Internaldate, IMAP4=route.imaplib.IMAP4))
    monkeypatch.setattr(route, "_ensure_quarantine", lambda imap_obj, folder: folder)

    resp = client.post(
        "/api/interception/release/99",
        json={"target_folder": "INBOX"},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200


def test_release_missing_raw_content_returns_error(monkeypatch, client):
    _login(client)
    conn = get_db()
    conn.execute("DELETE FROM email_messages")
    conn.execute("DELETE FROM email_accounts")
    conn.execute(
        """
        INSERT INTO email_accounts
        (id, account_name, email_address, imap_host, imap_port, imap_username, imap_password, imap_use_ssl, is_active)
        VALUES (77, 'Missing Account', 'missing77@example.com', 'imap.missing.test', 993, 'missing_user', ?, 1, 1)
        """,
        (encrypt_credential("missing-secret"),),
    )
    conn.execute(
        """
        INSERT INTO email_messages
        (id, account_id, interception_status, status, subject, body_text, direction, original_uid, message_id)
        VALUES (120, 77, 'HELD', 'PENDING', 'No Raw', 'Body', 'inbound', 0, '<missing@example.com>')
        """
    )
    conn.commit()

    fake_imap = ReleaseIMAP("imap.missing.test", 993)
    monkeypatch.setattr(route, "imaplib", SimpleNamespace(IMAP4_SSL=lambda *args, **kwargs: fake_imap, Time2Internaldate=route.imaplib.Time2Internaldate, IMAP4=route.imaplib.IMAP4))
    monkeypatch.setattr(route, "_ensure_quarantine", lambda imap_obj, folder: folder)

    resp = client.post(
        "/api/interception/release/120",
        json={"target_folder": "INBOX"},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 500
    assert resp.get_json()["reason"] == "raw-missing"
