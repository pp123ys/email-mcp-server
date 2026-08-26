"""配置服务：账号状态、配置写入与连接验证。"""
from __future__ import annotations

import os
from typing import Literal, cast

import pydantic

from email_mcp.config import save_account
from email_mcp.context import AppContext
from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.imap_client import IMAPClient
from email_mcp.provider.smtp_client import SMTPClient

REQUIRED_ENV_KEYS = [
    "EMAIL_IMAP_HOST",
    "EMAIL_SMTP_HOST",
    "EMAIL_USERNAME",
    "EMAIL_AUTH_SECRET",
]


class ConfigService:
    """账号配置状态查询、写入与连接验证。"""

    def __init__(
        self,
        ctx: AppContext,
        env_path: str | None = None,
        retry_attempts: int = 1,
        retry_delay_base: float = 0.0,
    ):
        self.ctx = ctx
        self.env_path = env_path
        self.retry_attempts = retry_attempts
        self.retry_delay_base = retry_delay_base

    def get_account_status(self) -> dict[str, object]:
        """返回配置状态：已配置返回账号信息（不含密钥），未配置返回缺失字段。"""
        if self.ctx.configured and self.ctx.account is not None:
            account = self.ctx.account
            return {
                "success": True,
                "data": {
                    "configured": True,
                    "account": {
                        "account_id": account.account_id,
                        "username": account.username,
                        "imap_host": account.imap_host,
                        "imap_port": account.imap_port,
                        "imap_ssl": account.imap_ssl,
                        "smtp_host": account.smtp_host,
                        "smtp_port": account.smtp_port,
                        "smtp_ssl": account.smtp_ssl,
                        "auth_mode": account.auth_mode,
                        "sent_folder": account.sent_folder,
                    },
                },
            }
        missing = [key for key in REQUIRED_ENV_KEYS if not os.getenv(key)]
        return {"success": True, "data": {"configured": False, "missing": missing}}

    def configure_account(
        self,
        *,
        imap_host: str,
        imap_port: int = 993,
        imap_ssl: bool = True,
        smtp_host: str,
        smtp_port: int = 465,
        smtp_ssl: bool = True,
        username: str,
        auth_secret: str,
        auth_mode: str = "app_password",
        sent_folder: str = "Sent",
    ) -> dict[str, object]:
        """校验并写入账号配置，热重载上下文。auth_secret 为敏感信息。"""
        if not auth_secret.strip():
            return error_result(ErrorCode.CONFIG_INVALID, "auth_secret 不能为空")
        if not username.strip() or not imap_host.strip() or not smtp_host.strip():
            return error_result(
                ErrorCode.CONFIG_INVALID, "username/imap_host/smtp_host 不能为空"
            )
        if auth_mode not in ("app_password", "password"):
            return error_result(
                ErrorCode.CONFIG_INVALID,
                f"auth_mode 只能是 app_password 或 password，收到 {auth_mode!r}",
            )
        auth_mode_value = cast(Literal["app_password", "password"], auth_mode)
        try:
            account = Account(
                imap_host=imap_host,
                imap_port=imap_port,
                imap_ssl=imap_ssl,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_ssl=smtp_ssl,
                username=username,
                auth_mode=auth_mode_value,
                auth_secret=auth_secret,
                sent_folder=sent_folder,
            )
        except pydantic.ValidationError as exc:
            return error_result(
                ErrorCode.CONFIG_INVALID,
                f"账号配置不合法: {exc.errors()[0]['msg'] if exc.errors() else '校验失败'}",
            )
        except Exception as exc:
            sealed = EmailMCPError.from_exception(exc)
            return error_result(sealed.code, sealed.message)
        try:
            save_account(account, self.env_path)
        except OSError as exc:
            return error_result(ErrorCode.CONFIG_INVALID, f"写入配置失败: {exc}")
        self.ctx.reload(account)
        self.ctx.start_scheduler()  # 热重载后调度立即生效（幂等）
        return {"success": True, "data": {"configured": True, "username": account.username}}

    def test_email_connection(self) -> dict[str, object]:
        """用当前配置试连 IMAP 与 SMTP（仅登录验证，不发送邮件）。"""
        if not self.ctx.configured or self.ctx.account is None:
            return error_result(
                ErrorCode.CONFIG_MISSING, "邮箱尚未配置，请先调用 configure_account"
            )
        account = self.ctx.account
        results: dict[str, object] = {}
        try:
            with IMAPClient(
                account,
                retry_attempts=self.retry_attempts,
                retry_delay_base=self.retry_delay_base,
            ).connect():
                results["imap"] = {"ok": True}
        except EmailMCPError as exc:
            results["imap"] = {"ok": False, "code": str(exc.code), "message": exc.message}
        try:
            SMTPClient(
                account,
                retry_attempts=self.retry_attempts,
                retry_delay_base=self.retry_delay_base,
            ).check()
            results["smtp"] = {"ok": True}
        except EmailMCPError as exc:
            results["smtp"] = {"ok": False, "code": str(exc.code), "message": exc.message}
        return {"success": True, "data": {"results": results}}
