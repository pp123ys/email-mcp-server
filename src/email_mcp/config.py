from __future__ import annotations

import os
from typing import Literal, cast

from dotenv import load_dotenv

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account


def _require_port(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except ValueError:
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID, f"{name} 必须是数字，收到 {raw!r}"
        ) from None


def load_account(env_path: str | None = None) -> Account:
    """从 .env / 环境变量构建 Account。缺必填项抛 CONFIG_MISSING。"""
    if env_path:
        load_dotenv(env_path, override=True)
    else:
        load_dotenv()

    def require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise EmailMCPError(ErrorCode.CONFIG_MISSING, f"缺少环境变量 {name}")
        return value

    auth_mode_raw = os.getenv("EMAIL_AUTH_MODE", "app_password")
    if auth_mode_raw not in ("app_password", "password"):
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID,
            f"EMAIL_AUTH_MODE 只能是 app_password 或 password，收到 {auth_mode_raw!r}",
        )
    auth_mode = cast(Literal["app_password", "password"], auth_mode_raw)

    return Account(
        account_id=os.getenv("EMAIL_ACCOUNT_ID", "default"),
        imap_host=require("EMAIL_IMAP_HOST"),
        imap_port=_require_port("EMAIL_IMAP_PORT", 993),
        imap_ssl=os.getenv("EMAIL_IMAP_SSL", "true").lower() == "true",
        smtp_host=require("EMAIL_SMTP_HOST"),
        smtp_port=_require_port("EMAIL_SMTP_PORT", 465),
        smtp_ssl=os.getenv("EMAIL_SMTP_SSL", "true").lower() == "true",
        username=require("EMAIL_USERNAME"),
        auth_mode=auth_mode,
        auth_secret=require("EMAIL_AUTH_SECRET"),
        sent_folder=os.getenv("EMAIL_SENT_FOLDER", "Sent"),
    )


def send_rate_limit() -> int:
    """每分钟发送上限（默认 10）。"""
    try:
        return int(os.getenv("EMAIL_SEND_RATE_LIMIT", "10"))
    except ValueError:
        return 10


def http_token() -> str | None:
    """HTTP 模式 Bearer token；为空则只监听 localhost。"""
    return os.getenv("EMAIL_HTTP_TOKEN") or None
