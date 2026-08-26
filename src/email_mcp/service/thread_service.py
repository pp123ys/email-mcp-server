from __future__ import annotations

from typing import Any

from email_mcp.errors import ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider


class ThreadService:
    """会话线程聚合。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    def get_thread(self, email_id: str) -> dict[str, Any]:
        try:
            folder, uid = email_id.rsplit(":", 1)
        except ValueError:
            return error_result(
                ErrorCode.CONFIG_INVALID, f"email_id 格式应为 folder:uid，收到 {email_id!r}"
            )
        try:
            seed = self.provider.get_message(self.account, folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        thread = self.provider.get_thread(self.account, seed.message_id)
        return {"success": True, "data": [m.model_dump(mode="json") for m in thread]}
