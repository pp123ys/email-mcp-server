from __future__ import annotations

import re
from typing import Any

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.ids import parse_email_id
from email_mcp.service.validators import validate_recipients

_MAILTO_RE = re.compile(r"mailto:([^?>\s]+)")
_URL_RE = re.compile(r"<((?:https?):[^>]+)>")


def parse_list_unsubscribe(header: str | None) -> dict[str, str | None] | None:
    """解析 List-Unsubscribe 头。返回 {'mailto': ..., 'url': ...} 或 None。"""
    if not header:
        return None
    mailto = _MAILTO_RE.search(header)
    url = _URL_RE.search(header)
    return {
        "mailto": mailto.group(1) if mailto else None,
        "url": url.group(1) if url else None,
    }


class UnsubscribeService:
    """基于 List-Unsubscribe 头的退订。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    @staticmethod
    def _find_header(headers: dict[str, str], name: str) -> str | None:
        """大小写不敏感的头查找（RFC 头名不区分大小写）。"""
        lower = name.lower()
        for key, value in headers.items():
            if key.lower() == lower:
                return value
        return None

    def unsubscribe(self, email_id: str) -> dict[str, Any]:
        try:
            folder, uid = parse_email_id(email_id)
        except EmailMCPError as e:
            return error_result(e.code, e.message)
        try:
            headers = self.provider.get_headers(self.account, folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        except EmailMCPError as e:
            return error_result(e.code, e.message, e.details)
        except Exception as exc:  # 兜底：provider 异常收敛为 INTERNAL
            sealed = EmailMCPError.from_exception(exc, secrets=[self.account.auth_secret])
            return error_result(sealed.code, sealed.message)

        info = parse_list_unsubscribe(self._find_header(headers, "List-Unsubscribe"))
        if info is None or info["mailto"] is None:
            return error_result(
                ErrorCode.UNSUBSCRIBE_UNSUPPORTED,
                "该邮件没有可用的 mailto 退订地址",
                {"parsed": info},
            )
        try:
            # 校验退订地址：防止恶意头让 SMTP 向任意地址发信
            validate_recipients([info["mailto"]])
        except EmailMCPError as e:
            return error_result(e.code, e.message, e.details)
        try:
            self.provider.send(
                self.account, to=[info["mailto"]], cc=None,
                subject="unsubscribe", body="",
            )
        except EmailMCPError as e:
            return error_result(e.code, e.message, e.details)
        except Exception as exc:  # 兜底
            sealed = EmailMCPError.from_exception(exc, secrets=[self.account.auth_secret])
            return error_result(sealed.code, sealed.message)
        return {"success": True, "data": {"unsubscribed_to": info["mailto"]}}
