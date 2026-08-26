"""邮件 ID 解析。"""
from __future__ import annotations

from email_mcp.errors import EmailMCPError, ErrorCode


def parse_email_id(email_id: str) -> tuple[str, str]:
    """解析 'folder:uid'（按最后一个冒号切分），非法格式抛 CONFIG_INVALID。"""
    if not isinstance(email_id, str) or ":" not in email_id:
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID, f"email_id 格式应为 folder:uid，收到 {email_id!r}"
        )
    folder, uid = email_id.rsplit(":", 1)
    if not folder or not uid:
        raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"email_id 格式不合法: {email_id!r}")
    return folder, uid
