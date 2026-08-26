from __future__ import annotations

from typing import Protocol

from email_mcp.models import Account, AttachmentMeta, EmailMessage


class EmailProvider(Protocol):
    """邮件提供者抽象接口。

    第一版实现：ImapProvider（imaplib + smtplib）。
    未来实现：GmailProvider（Gmail API）、OutlookProvider（Graph API）。
    新增提供者 = 新增一个实现文件 + 注册，不改动上三层。
    """

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
        """列出文件夹中的邮件，返回 (消息列表, 总数)。page 从 1 开始。"""
        ...

    def get_message(self, account: Account, folder: str, uid: str) -> EmailMessage:
        """按 folder + uid 读取单封邮件。"""
        ...

    def get_thread(self, account: Account, message_id: str) -> list[EmailMessage]:
        """按 Message-ID 拉取整条会话线程（在 INBOX 与 Sent 中搜索）。"""
        ...

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
        """关键词/发件人/日期范围搜索。since/until 为 ISO 日期字符串。"""
        ...

    def list_folders(self, account: Account) -> list[str]:
        """列出所有文件夹（标签映射为文件夹）。"""
        ...

    def get_attachments(
        self, account: Account, folder: str, uid: str
    ) -> list[AttachmentMeta]:
        """列出邮件附件元信息。"""
        ...

    def download_attachment(
        self, account: Account, folder: str, uid: str, part_id: str
    ) -> bytes:
        """按 part_id 下载附件内容。"""
        ...

    def get_headers(self, account: Account, folder: str, uid: str) -> dict[str, str]:
        """读取原始 RFC 822 头。"""
        ...

    def save_draft(
        self,
        account: Account,
        *,
        to: list[str],
        cc: list[str] | None,
        subject: str,
        body: str,
    ) -> str:
        """存草稿到 Drafts 文件夹，返回草稿 id（folder:uid）。"""
        ...

    def list_drafts(self, account: Account) -> list[EmailMessage]:
        """列出草稿。"""
        ...

    def send(
        self,
        account: Account,
        *,
        to: list[str],
        cc: list[str] | None,
        subject: str,
        body: str,
    ) -> str:
        """发送邮件，返回发送的 Message-ID。"""
        ...

    def mark_read(self, account: Account, folder: str, uid: str) -> None: ...
    def mark_unread(self, account: Account, folder: str, uid: str) -> None: ...
    def move(self, account: Account, folder: str, uid: str, dest_folder: str) -> None: ...
    def trash(self, account: Account, folder: str, uid: str) -> None: ...
    def archive(self, account: Account, folder: str, uid: str) -> None: ...
    def set_flag(
        self, account: Account, folder: str, uid: str, flag: str
    ) -> None: ...
