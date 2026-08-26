from __future__ import annotations

import os
from pathlib import Path
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


def load_account(env_path: str | None = None, strict: bool = True) -> Account | None:
    """从 .env / 环境变量构建 Account。

    strict=True（默认）：缺必填项抛 CONFIG_MISSING。
    strict=False：缺必填项返回 None（供无凭据启动，由 configure_account 工具配置）。
    """
    if env_path:
        load_dotenv(env_path, override=True)
    else:
        load_dotenv()

    auth_mode_raw = os.getenv("EMAIL_AUTH_MODE", "app_password")
    if auth_mode_raw not in ("app_password", "password"):
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID,
            f"EMAIL_AUTH_MODE 只能是 app_password 或 password，收到 {auth_mode_raw!r}",
        )
    auth_mode = cast(Literal["app_password", "password"], auth_mode_raw)

    values = {
        "EMAIL_IMAP_HOST": os.getenv("EMAIL_IMAP_HOST"),
        "EMAIL_SMTP_HOST": os.getenv("EMAIL_SMTP_HOST"),
        "EMAIL_USERNAME": os.getenv("EMAIL_USERNAME"),
        "EMAIL_AUTH_SECRET": os.getenv("EMAIL_AUTH_SECRET"),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        if strict:
            raise EmailMCPError(ErrorCode.CONFIG_MISSING, f"缺少环境变量 {missing[0]}")
        return None

    return Account(
        account_id=os.getenv("EMAIL_ACCOUNT_ID", "default"),
        imap_host=values["EMAIL_IMAP_HOST"] or "",
        imap_port=_require_port("EMAIL_IMAP_PORT", 993),
        imap_ssl=os.getenv("EMAIL_IMAP_SSL", "true").lower() == "true",
        smtp_host=values["EMAIL_SMTP_HOST"] or "",
        smtp_port=_require_port("EMAIL_SMTP_PORT", 465),
        smtp_ssl=os.getenv("EMAIL_SMTP_SSL", "true").lower() == "true",
        username=values["EMAIL_USERNAME"] or "",
        auth_mode=auth_mode,
        auth_secret=values["EMAIL_AUTH_SECRET"] or "",
        sent_folder=os.getenv("EMAIL_SENT_FOLDER", "Sent"),
    )


def save_account(account: Account, env_path: str | None = None) -> None:
    """把 Account 配置合并写入 .env（保留已有非冲突键），供 configure_account 工具调用。"""
    path = Path(env_path) if env_path else Path(".env")
    existing: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, _, value = line.partition("=")
                existing[key.strip()] = value.strip()
    existing.update(
        {
            "EMAIL_ACCOUNT_ID": account.account_id,
            "EMAIL_IMAP_HOST": account.imap_host,
            "EMAIL_IMAP_PORT": str(account.imap_port),
            "EMAIL_IMAP_SSL": str(account.imap_ssl).lower(),
            "EMAIL_SMTP_HOST": account.smtp_host,
            "EMAIL_SMTP_PORT": str(account.smtp_port),
            "EMAIL_SMTP_SSL": str(account.smtp_ssl).lower(),
            "EMAIL_USERNAME": account.username,
            "EMAIL_AUTH_MODE": account.auth_mode,
            "EMAIL_AUTH_SECRET": account.auth_secret,
            "EMAIL_SENT_FOLDER": account.sent_folder,
        }
    )
    lines = [f"{key}={value}" for key, value in existing.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def send_rate_limit() -> int:
    """每分钟发送上限（默认 10）。"""
    try:
        return int(os.getenv("EMAIL_SEND_RATE_LIMIT", "10"))
    except ValueError:
        return 10


def http_token() -> str | None:
    """HTTP 模式预留的 Bearer token；当前 mcp 1.29.1 不支持静态认证，设置后仅产生警告。"""
    return os.getenv("EMAIL_HTTP_TOKEN") or None
