from __future__ import annotations

import email
import re
from datetime import datetime
from email import policy

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account, AttachmentMeta, EmailMessage
from email_mcp.provider.imap_client import IMAPClient
from email_mcp.provider.parser import find_part_by_path, parse_email_message
from email_mcp.provider.smtp_client import SMTPClient


def _fetch_rfc822(
    fetch: list[None] | list[bytes | tuple[bytes, bytes]],
) -> bytes | None:
    """从 FETCH 响应提取 RFC 822 原始字节；无数据返回 None。"""
    if not fetch:
        return None
    entry = fetch[0]
    if entry is None or isinstance(entry, bytes):
        return None
    return entry[1]


class ImapProvider:
    """EmailProvider 的 IMAP/SMTP 实现。"""

    def __init__(
        self,
        imap_client: IMAPClient | None = None,
        smtp_client: SMTPClient | None = None,
    ):
        self._imap_client = imap_client
        self._smtp_client = smtp_client

    def _imap(self, account: Account) -> IMAPClient:
        return self._imap_client or IMAPClient(account)

    def _smtp(self, account: Account) -> SMTPClient:
        return self._smtp_client or SMTPClient(account)

    def list_messages(
        self,
        account: Account,
        folder: str,
        *,
        page: int,
        page_size: int,
        unread_only: bool = False,
        from_email: str | None = None,
    ) -> tuple[list[EmailMessage], int]:
        with self._imap(account).connect() as conn:
            typ, _ = conn.select(folder, readonly=True)
            if typ != "OK":
                raise EmailMCPError(ErrorCode.FOLDER_NOT_FOUND, f"文件夹不存在: {folder}")
            criteria: list[str] = []
            if unread_only:
                criteria.append("UNSEEN")
            if from_email:
                criteria.append(f'FROM "{from_email}"')
            status, data = (
                conn.uid("SEARCH", *criteria) if criteria else conn.uid("SEARCH", "ALL")
            )
            if status != "OK":
                return [], 0
            uids = data[0].split() if data and data[0] else []
            total = len(uids)
            start = (page - 1) * page_size
            batch = uids[start : start + page_size]
            messages: list[EmailMessage] = []
            for uid in batch:
                status, fetch = conn.uid("FETCH", uid, "(RFC822)")
                if status == "OK":
                    raw = _fetch_rfc822(fetch)
                    if raw is not None:
                        messages.append(
                            parse_email_message(raw, folder=folder, uid=uid.decode())
                        )
            return messages, total

    def get_message(self, account: Account, folder: str, uid: str) -> EmailMessage:
        with self._imap(account).connect() as conn:
            conn.select(folder, readonly=True)
            status, fetch = conn.uid("FETCH", uid, "(RFC822)")
            if status != "OK":
                raise KeyError(f"{folder}:{uid}")
            raw = _fetch_rfc822(fetch)
            if raw is None:
                raise KeyError(f"{folder}:{uid}")
            return parse_email_message(raw, folder=folder, uid=uid)

    def get_thread(self, account: Account, message_id: str) -> list[EmailMessage]:
        """链式解析：种子 + In-Reply-To/References 祖先与后代，去重按 Message-ID，按日期排序。"""
        with self._imap(account).connect() as conn:
            results: dict[str, EmailMessage] = {}
            frontier: list[str] = [message_id]
            visited: set[str] = set()
            while frontier:
                mid = frontier.pop()
                if not mid or mid in visited:
                    continue
                visited.add(mid)
                for folder in ("INBOX", account.sent_folder):
                    typ, _ = conn.select(folder, readonly=True)
                    if typ != "OK":
                        continue
                    for header in ("Message-ID", "In-Reply-To", "References"):
                        status, data = conn.uid("SEARCH", "HEADER", header, f'"{mid}"')
                        if status != "OK" or not data or not data[0]:
                            continue
                        for uid in data[0].split():
                            status, fetch = conn.uid("FETCH", uid, "(RFC822)")
                            if status == "OK":
                                raw = _fetch_rfc822(fetch)
                                if raw is not None:
                                    msg = parse_email_message(
                                        raw, folder=folder, uid=uid.decode()
                                    )
                                    key = msg.message_id or f"{folder}:{uid.decode()}"
                                    results[key] = msg
                                    if msg.message_id:
                                        frontier.append(msg.message_id)
                                    if msg.in_reply_to:
                                        frontier.append(msg.in_reply_to)
                                    refs = msg.headers.get("References")
                                    if refs:
                                        frontier.extend(re.findall(r"<[^>]+>", refs))
            return sorted(results.values(), key=lambda m: m.date)

    def search(
        self,
        account: Account,
        *,
        query: str = "",
        from_email: str | None = None,
        since: str | None = None,
        until: str | None = None,
        folder: str = "INBOX",
    ) -> list[EmailMessage]:
        with self._imap(account).connect() as conn:
            typ, _ = conn.select(folder, readonly=True)
            if typ != "OK":
                return []
            criteria: list[str] = ["ALL"]
            if query:
                criteria = ["TEXT", f'"{query}"']
            if from_email:
                criteria += ["FROM", f'"{from_email}"']
            if since:
                criteria += ["SINCE", _imap_date(since)]
            if until:
                criteria += ["BEFORE", _imap_date(until)]
            status, data = conn.uid("SEARCH", *criteria)
            if status != "OK" or not data or not data[0]:
                return []
            messages: list[EmailMessage] = []
            for uid in data[0].split():
                status, fetch = conn.uid("FETCH", uid, "(RFC822)")
                if status == "OK":
                    raw = _fetch_rfc822(fetch)
                    if raw is not None:
                        messages.append(
                            parse_email_message(raw, folder=folder, uid=uid.decode())
                        )
            return messages

    def list_folders(self, account: Account) -> list[str]:
        with self._imap(account).connect() as conn:
            status, data = conn.list()
            folders: list[str] = []
            for item in data:
                if isinstance(item, bytes):
                    decoded = item.decode(errors="replace")
                    parts = decoded.split('"')
                    if len(parts) >= 3 and parts[-2].strip():
                        folders.append(parts[-2].strip())
            return folders

    def create_folder(self, account: Account, name: str) -> None:
        with self._imap(account).connect() as conn:
            status, _ = conn.create(name)
            if status != "OK":
                raise EmailMCPError(ErrorCode.INTERNAL, f"创建文件夹失败: {name}")

    def delete_folder(self, account: Account, name: str) -> None:
        with self._imap(account).connect() as conn:
            status, _ = conn.delete(name)
            if status != "OK":
                raise EmailMCPError(ErrorCode.INTERNAL, f"删除文件夹失败: {name}")

    def get_attachments(
        self, account: Account, folder: str, uid: str
    ) -> list[AttachmentMeta]:
        return self.get_message(account, folder, uid).attachments

    def download_attachment(
        self, account: Account, folder: str, uid: str, part_id: str
    ) -> bytes:
        with self._imap(account).connect() as conn:
            conn.select(folder, readonly=True)
            status, fetch = conn.uid("FETCH", uid, "(RFC822)")
            if status != "OK":
                raise KeyError(f"{folder}:{uid}")
            raw = _fetch_rfc822(fetch)
            if raw is None:
                raise KeyError(f"{folder}:{uid}")
        msg = email.message_from_bytes(raw, policy=policy.default)
        path = tuple(int(x) for x in part_id.split("."))
        part = find_part_by_path(msg, path)
        if part is None:
            raise EmailMCPError(ErrorCode.ATTACHMENT_NOT_FOUND, f"附件 {part_id} 不存在")
        payload = part.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload
        return b""

    def get_headers(self, account: Account, folder: str, uid: str) -> dict[str, str]:
        return self.get_message(account, folder, uid).headers

    def save_draft(
        self,
        account: Account,
        *,
        to: list[str],
        cc: list[str] | None = None,
        subject: str,
        body: str,
    ) -> str:
        with self._imap(account).connect() as conn:
            conn.select("Drafts")
            from email.message import EmailMessage as Em

            draft = Em()
            draft["From"] = account.username
            draft["To"] = ", ".join(to)
            if cc:
                draft["Cc"] = ", ".join(cc)
            draft["Subject"] = subject
            draft.set_content(body)
            status, data = conn.append("Drafts", None, None, draft.as_bytes())
            if status != "OK":
                raise EmailMCPError(ErrorCode.INTERNAL, "保存草稿失败")
            return f"Drafts:{data[0].decode()}"

    def list_drafts(self, account: Account) -> list[EmailMessage]:
        with self._imap(account).connect() as conn:
            typ, _ = conn.select("Drafts", readonly=True)
            if typ != "OK":
                return []
            status, data = conn.uid("SEARCH", "ALL")
            if status != "OK" or not data or not data[0]:
                return []
            drafts: list[EmailMessage] = []
            for uid in data[0].split():
                status, fetch = conn.uid("FETCH", uid, "(RFC822)")
                if status == "OK":
                    raw = _fetch_rfc822(fetch)
                    if raw is not None:
                        drafts.append(
                            parse_email_message(raw, folder="Drafts", uid=uid.decode())
                        )
            return drafts

    def send(
        self,
        account: Account,
        *,
        to: list[str],
        cc: list[str] | None = None,
        subject: str,
        body: str,
    ) -> str:
        return self._smtp(account).send(
            to=to, cc=cc, subject=subject, body=body, sender=account.username
        )

    def _store_flags(
        self, account: Account, folder: str, uid: str, add: bool, flags: str
    ) -> None:
        with self._imap(account).connect() as conn:
            conn.select(folder)
            if add:
                conn.uid("STORE", uid, "+FLAGS", flags)
            else:
                conn.uid("STORE", uid, "-FLAGS", flags)

    def mark_read(self, account: Account, folder: str, uid: str) -> None:
        self._store_flags(account, folder, uid, True, "(\\Seen)")

    def mark_unread(self, account: Account, folder: str, uid: str) -> None:
        self._store_flags(account, folder, uid, False, "(\\Seen)")

    def set_flag(self, account: Account, folder: str, uid: str, flag: str) -> None:
        self._store_flags(account, folder, uid, True, f"({flag})")

    def move(self, account: Account, folder: str, uid: str, dest_folder: str) -> None:
        with self._imap(account).connect() as conn:
            conn.select(folder)
            conn.uid("COPY", uid, dest_folder)
            conn.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
            conn.expunge()

    def trash(self, account: Account, folder: str, uid: str) -> None:
        self.move(account, folder, uid, "Trash")

    def archive(self, account: Account, folder: str, uid: str) -> None:
        self.move(account, folder, uid, "All Mail")


def _imap_date(iso_date: str) -> str:
    dt = datetime.fromisoformat(iso_date)
    return dt.strftime("%d-%b-%Y")
