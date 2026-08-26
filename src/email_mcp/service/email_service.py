from __future__ import annotations

from collections.abc import Callable
from typing import Any

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.pagination import page_meta
from email_mcp.service.validators import validate_recipients


class EmailService:
    """工具层与 Provider 之间的业务门面。所有方法返回 MCP 工具可直接序列化的 dict。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    # ---- 工具方法 ----

    def _parse_email_id(self, email_id: str) -> tuple[str, str]:
        """邮件 ID 格式 'folder:uid'，按最后一个冒号切分。"""
        if ":" not in email_id:
            raise EmailMCPError(
                ErrorCode.CONFIG_INVALID, f"email_id 格式应为 folder:uid，收到 {email_id!r}"
            )
        folder, uid = email_id.rsplit(":", 1)
        if not folder or not uid:
            raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"email_id 格式不合法: {email_id!r}")
        return folder, uid

    def _wrap(self, fn: Callable[[], Any]) -> dict[str, Any]:
        """把业务调用包成 {success: True, data} / {success: False, error}。"""
        try:
            return {"success": True, "data": fn()}
        except EmailMCPError as e:
            return error_result(e.code, e.message, e.details)
        except Exception as exc:  # 兜底：任何未预期异常都收敛为 INTERNAL
            sealed = EmailMCPError.from_exception(exc)
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
            return {"filename": part_id, "content_base64": base64.b64encode(content).decode()}
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
