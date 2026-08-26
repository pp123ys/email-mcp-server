from __future__ import annotations

from typing import Any

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.ids import parse_email_id


class ThreadService:
    """会话线程聚合。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    def get_thread(self, email_id: str) -> dict[str, Any]:
        try:
            folder, uid = parse_email_id(email_id)
        except EmailMCPError as e:
            return error_result(e.code, e.message)
        try:
            seed = self.provider.get_message(self.account, folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        except Exception as exc:  # 兜底：provider 异常收敛为 INTERNAL
            sealed = EmailMCPError.from_exception(exc, secrets=[self.account.auth_secret])
            return error_result(sealed.code, sealed.message)
        try:
            thread = self.provider.get_thread(self.account, seed.message_id)
        except Exception as exc:
            sealed = EmailMCPError.from_exception(exc, secrets=[self.account.auth_secret])
            return error_result(sealed.code, sealed.message)
        return {"success": True, "data": [m.model_dump(mode="json") for m in thread]}
