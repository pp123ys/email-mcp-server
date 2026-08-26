"""内存版 EmailProvider 实现：服务层单元测试用。"""
from __future__ import annotations

from datetime import datetime, timezone

from email_mcp.models import EmailAddress, EmailMessage

_SEEN = "\\Seen"


def make_message(
    uid: int,
    folder: str = "INBOX",
    subject: str = "subject",
    body: str = "body",
    read: bool = True,
    from_addr: str = "sender@x.com",
    message_id: str = "",
    in_reply_to: str | None = None,
) -> EmailMessage:
    return EmailMessage(
        id=f"{folder}:{uid}",
        account_id="default",
        folder=folder,
        subject=subject,
        from_=EmailAddress(email=from_addr),
        to=[EmailAddress(email="me@x.com")],
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        flags=[_SEEN] if read else [],
        body=body,
        message_id=message_id or f"msg-{uid}@x.com",
        in_reply_to=in_reply_to,
    )


class FakeProvider:
    """实现 EmailProvider 协议的内存替身。"""

    def __init__(self, messages: list[EmailMessage] | None = None):
        self.messages: list[EmailMessage] = messages or []
        self.sent: list[dict] = []
        self.drafts: list[EmailMessage] = []

    def list_messages(
        self, account, folder, *, page, page_size, unread_only=False, from_email=None
    ):
        items = [m for m in self.messages if m.folder == folder]
        if unread_only:
            items = [m for m in items if _SEEN not in m.flags]
        if from_email:
            items = [m for m in items if m.from_.email == from_email]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def get_message(self, account, folder, uid):
        for m in self.messages:
            if m.folder == folder and m.id.endswith(f":{uid}"):
                return m
        raise KeyError(f"message {folder}:{uid} not found")

    def get_thread(self, account, message_id):
        by_id = {m.message_id: m for m in self.messages if m.message_id}
        collected: dict[str, EmailMessage] = {}
        stack = [message_id]
        while stack:
            mid = stack.pop()
            if not mid or mid in collected or mid not in by_id:
                continue
            m = by_id[mid]
            collected[mid] = m
            if m.in_reply_to:
                stack.append(m.in_reply_to)
            for other in self.messages:
                if other.in_reply_to == mid:
                    stack.append(other.message_id)
        return sorted(collected.values(), key=lambda m: m.date)

    def search(self, account, *, query="", from_email=None, since=None, until=None, folder="INBOX"):
        items = [m for m in self.messages if m.folder == folder]
        if query:
            items = [
                m
                for m in items
                if query.lower() in m.subject.lower() or query.lower() in m.body.lower()
            ]
        if from_email:
            items = [m for m in items if m.from_.email == from_email]
        return items

    def list_folders(self, account):
        return sorted({m.folder for m in self.messages} | {"INBOX", "Sent"})

    def get_attachments(self, account, folder, uid):
        return self.get_message(account, folder, uid).attachments

    def download_attachment(self, account, folder, uid, part_id):
        self.get_message(account, folder, uid)  # 消息不存在时抛 KeyError
        return b"fake-content"

    def get_headers(self, account, folder, uid):
        m = self.get_message(account, folder, uid)
        return {"Subject": m.subject, "From": m.from_.email, "Message-ID": m.message_id}

    def save_draft(self, account, *, to, cc=None, subject, body):
        draft = make_message(
            uid=len(self.drafts) + 100, folder="Drafts", subject=subject, body=body
        )
        self.drafts.append(draft)
        self.messages.append(draft)
        return draft.id

    def list_drafts(self, account):
        return self.drafts

    def send(self, account, *, to, cc=None, subject, body):
        self.sent.append({"to": to, "cc": cc, "subject": subject, "body": body})
        return f"sent-{len(self.sent)}@x.com"

    def mark_read(self, account, folder, uid):
        self.get_message(account, folder, uid).flags.append(_SEEN)

    def mark_unread(self, account, folder, uid):
        m = self.get_message(account, folder, uid)
        m.flags = [f for f in m.flags if f != _SEEN]

    def move(self, account, folder, uid, dest_folder):
        m = self.get_message(account, folder, uid)
        m.folder = dest_folder
        m.id = f"{dest_folder}:{uid}"

    def trash(self, account, folder, uid):
        self.move(account, folder, uid, "Trash")

    def archive(self, account, folder, uid):
        self.move(account, folder, uid, "All Mail")

    def set_flag(self, account, folder, uid, flag):
        m = self.get_message(account, folder, uid)
        if flag not in m.flags:
            m.flags.append(flag)
