from __future__ import annotations

from collections.abc import Callable
from typing import Any

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.ids import parse_email_id
from email_mcp.service.pagination import page_meta
from email_mcp.service.quoting import build_quote_block
from email_mcp.service.scheduler import SchedulerStore
from email_mcp.service.validators import validate_recipients

_ALLOWED_FLAGS = frozenset({"\\Flagged", "\\Seen", "\\Answered", "\\Draft", "\\Deleted"})


def _validate_flag(flag: str) -> None:
    """校验 IMAP 标记；只允许系统标记或 $ 开头的关键字标记。"""
    if flag not in _ALLOWED_FLAGS and not flag.startswith("$"):
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID,
            (
                f"不支持的邮件标记: {flag!r}"
                "（允许 \\Flagged/\\Seen/\\Answered/\\Draft/\\Deleted 或 $ 开头关键字）"
            ),
        )


class EmailService:
    """工具层与 Provider 之间的业务门面。所有方法返回 MCP 工具可直接序列化的 dict。"""

    def __init__(
        self,
        provider: EmailProvider,
        account: Account,
        scheduler_store: SchedulerStore | None = None,
    ):
        self.provider = provider
        self.account = account
        # Task 20/21 的 snooze/定时发送工具将使用 scheduler_store
        self.scheduler_store = scheduler_store

    # ---- 工具方法 ----

    def _parse_email_id(self, email_id: str) -> tuple[str, str]:
        """邮件 ID 格式 'folder:uid'，按最后一个冒号切分。"""
        return parse_email_id(email_id)

    def _wrap(self, fn: Callable[[], Any]) -> dict[str, Any]:
        """把业务调用包成 {success: True, data} / {success: False, error}。"""
        try:
            return {"success": True, "data": fn()}
        except EmailMCPError as e:
            return error_result(e.code, e.message, e.details)
        except Exception as exc:  # 兜底：任何未预期异常都收敛为 INTERNAL
            sealed = EmailMCPError.from_exception(exc, secrets=[self.account.auth_secret])
            return error_result(sealed.code, sealed.message)

    # ---- 读取组 ----

    def list_inbox(
        self,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        from_email: str | None = None,
        folder: str = "INBOX",
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            msgs, total = self.provider.list_messages(
                self.account, folder,
                page=page, page_size=page_size,
                unread_only=unread_only, from_email=from_email,
            )
            # 注意：provider 已按页切片，这里只用其 total 计算元数据，绝不二次分页
            meta = page_meta(total, page, page_size)
            return {
                "items": [m.model_dump(mode="json") for m in msgs],
                "total": meta.total,
                "page": meta.page,
                "page_size": meta.page_size,
                "total_pages": meta.total_pages,
                "folder": folder,
            }
        return self._wrap(run)

    def read_email(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            try:
                msg = self.provider.get_message(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            return msg.model_dump(mode="json")
        return self._wrap(run)

    def search_emails(
        self,
        query: str = "",
        from_email: str | None = None,
        since: str | None = None,
        until: str | None = None,
        folder: str = "INBOX",
    ) -> dict[str, Any]:
        def run() -> list[dict[str, Any]]:
            msgs = self.provider.search(
                self.account,
                query=query, from_email=from_email,
                since=since, until=until, folder=folder,
            )
            return [m.model_dump(mode="json") for m in msgs]
        return self._wrap(run)

    def list_folders(self) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            return {"folders": self.provider.list_folders(self.account)}
        return self._wrap(run)

    def get_attachments(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            try:
                atts = self.provider.get_attachments(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            return {"attachments": [a.model_dump(mode="json") for a in atts]}
        return self._wrap(run)

    def download_attachment(self, email_id: str, part_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            try:
                content = self.provider.download_attachment(self.account, folder, uid, part_id)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            if len(content) > 25 * 1024 * 1024:
                raise EmailMCPError(ErrorCode.EMAIL_TOO_LARGE, "附件超过 25MB 上限")
            import base64
            return {"part_id": part_id, "content_base64": base64.b64encode(content).decode()}
        return self._wrap(run)

    def get_email_headers(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            try:
                headers = self.provider.get_headers(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            return {"headers": headers}
        return self._wrap(run)

    def get_account_info(self) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            return {
                "account_id": self.account.account_id,
                "username": self.account.username,
                "imap_host": self.account.imap_host,
                "smtp_host": self.account.smtp_host,
                "auth_mode": self.account.auth_mode,
            }
        return self._wrap(run)

    # ---- 发送与草稿 ----

    def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            if not to:
                raise EmailMCPError(ErrorCode.INVALID_RECIPIENT, "收件人列表不能为空")
            validate_recipients(to, cc)
            message_id = self.provider.send(
                self.account, to=to, cc=cc, subject=subject, body=body
            )
            return {"message_id": message_id}
        return self._wrap(run)

    def save_draft(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            validate_recipients(to, cc)
            draft_id = self.provider.save_draft(
                self.account, to=to, cc=cc, subject=subject, body=body
            )
            return {"draft_id": draft_id}
        return self._wrap(run)

    def list_drafts(self) -> dict[str, Any]:
        def run() -> list[dict[str, Any]]:
            drafts = self.provider.list_drafts(self.account)
            return [m.model_dump(mode="json") for m in drafts]
        return self._wrap(run)

    # ---- 操作组 ----

    def reply_email(
        self, email_id: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            try:
                original = self.provider.get_message(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            quote = build_quote_block(
                original.from_.name or original.from_.email,
                original.date.strftime("%Y-%m-%d %H:%M"),
                original.body,
            )
            full_body = f"{body}\n\n{quote}"
            validate_recipients([original.from_.email], cc)
            message_id = self.provider.send(
                self.account, to=[original.from_.email], cc=cc,
                subject=f"Re: {original.subject}", body=full_body,
            )
            return {"message_id": message_id, "original_email_id": original.id}
        return self._wrap(run)

    def forward_email(self, email_id: str, to: list[str], body: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            try:
                original = self.provider.get_message(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            quote = build_quote_block(
                original.from_.name or original.from_.email,
                original.date.strftime("%Y-%m-%d %H:%M"),
                original.body,
            )
            full_body = f"{body}\n\n---------- 转发 ----------\n{quote}"
            validate_recipients(to)
            message_id = self.provider.send(
                self.account, to=to, cc=None,
                subject=f"Fwd: {original.subject}", body=full_body,
            )
            return {"message_id": message_id}
        return self._wrap(run)

    def mark_read(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            self.provider.mark_read(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def mark_unread(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            self.provider.mark_unread(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def archive(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            self.provider.archive(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def move_email(self, email_id: str, dest_folder: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            self.provider.move(self.account, folder, uid, dest_folder)
            return {"email_id": email_id, "dest_folder": dest_folder}
        return self._wrap(run)

    def trash_email(self, email_id: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            folder, uid = self._parse_email_id(email_id)
            self.provider.trash(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def set_flag(self, email_id: str, flag: str = "\\Flagged") -> dict[str, Any]:
        def run() -> dict[str, Any]:
            _validate_flag(flag)
            folder, uid = self._parse_email_id(email_id)
            self.provider.set_flag(self.account, folder, uid, flag)
            return {"email_id": email_id, "flag": flag}
        return self._wrap(run)

    def pin_email(self, email_id: str) -> dict[str, Any]:
        return self.set_flag(email_id, "\\Flagged")

    def snooze_email(self, email_id: str, until: str) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            if self.scheduler_store is None:
                raise EmailMCPError(ErrorCode.CONFIG_MISSING, "调度器未初始化")
            from uuid import uuid4

            self.scheduler_store.add_snooze(
                {"id": str(uuid4()), "until": until, "email_id": email_id}
            )
            return {"email_id": email_id, "snoozed_until": until}
        return self._wrap(run)
