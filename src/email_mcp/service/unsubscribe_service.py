from __future__ import annotations

import re
from typing import Any

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.ids import parse_email_id

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

    def unsubscribe(self, email_id: str) -> dict[str, Any]:
        try:
            folder, uid = parse_email_id(email_id)
        except EmailMCPError as e:
            return error_result(e.code, e.message)
        try:
            headers = self.provider.get_headers(self.account, folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        except Exception as exc:  # 兜底：provider 异常收敛为 INTERNAL
            sealed = EmailMCPError.from_exception(exc)
            return error_result(sealed.code, sealed.message)

        info = parse_list_unsubscribe(headers.get("List-Unsubscribe"))
        if info is None or info["mailto"] is None:
            return error_result(
                ErrorCode.UNSUBSCRIBE_UNSUPPORTED,
                "该邮件没有可用的 mailto 退订地址",
                {"parsed": info},
            )
        try:
            self.provider.send(
                self.account, to=[info["mailto"]], cc=None,
                subject="unsubscribe", body="",
            )
        except Exception as exc:  # 兜底
            sealed = EmailMCPError.from_exception(exc)
            return error_result(sealed.code, sealed.message)
        return {"success": True, "data": {"unsubscribed_to": info["mailto"]}}
