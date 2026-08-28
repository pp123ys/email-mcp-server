from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext
from email_mcp.service.config_service import ConfigService
from email_mcp.tools._guard import async_run


def register(mcp: FastMCP, ctx: AppContext) -> None:
    service = ConfigService(ctx)

    @mcp.tool(
        description=(
            "查看邮箱配置状态：configured 布尔、缺失字段列表、"
            "已配置账号信息（不含密钥）"
        )
    )
    @async_run
    def get_account_status() -> dict[str, Any]:
        return service.get_account_status()

    @mcp.tool(
        description=(
            "配置邮箱账号（IMAP/SMTP 凭据）。首次运行或配置缺失时调用；"
            "auth_secret 为敏感信息，请先征得用户同意再写入；写入后立即生效并持久化到 .env"
        )
    )
    @async_run
    def configure_account(
        imap_host: str,
        smtp_host: str,
        username: str,
        auth_secret: str,
        imap_port: int = 993,
        imap_ssl: bool = True,
        smtp_port: int = 465,
        smtp_ssl: bool = True,
        auth_mode: str = "app_password",
        sent_folder: str = "Sent",
    ) -> dict[str, Any]:
        return service.configure_account(
            imap_host=imap_host, imap_port=imap_port, imap_ssl=imap_ssl,
            smtp_host=smtp_host, smtp_port=smtp_port, smtp_ssl=smtp_ssl,
            username=username, auth_secret=auth_secret,
            auth_mode=auth_mode, sent_folder=sent_folder,
        )

    @mcp.tool(description="用当前配置试连 IMAP 与 SMTP（仅登录验证，不发送邮件），返回逐项结果")
    @async_run
    def test_email_connection() -> dict[str, Any]:
        return service.test_email_connection()
