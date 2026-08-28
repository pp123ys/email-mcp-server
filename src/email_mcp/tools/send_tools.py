from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext
from email_mcp.service.email_service import EmailService
from email_mcp.tools._guard import async_run, guard


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册发送/草稿组工具。"""
    # 服务在 configure_account 热重载时重建，须每次调用时从 ctx 取当前实例
    def svc() -> EmailService:
        assert ctx.email_service is not None
        return ctx.email_service

    @mcp.tool(
        description=(
            "直接发送邮件（立即投递）；to 不能为空，cc 可选；"
            "如需人工确认请改用 save_draft 存草稿后手动发送"
        )
    )
    @async_run
    @guard(ctx)
    def send_email(
        to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any]:
        return svc().send_email(to=to, cc=cc, subject=subject, body=body)

    @mcp.tool(
        description=(
            "存草稿到 Drafts 文件夹（人工确认后手动发送）；"
            "to 可为空（先起草后补收件人），cc 可选"
        )
    )
    @async_run
    @guard(ctx)
    def save_draft(
        to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any]:
        return svc().save_draft(to=to, cc=cc, subject=subject, body=body)

    @mcp.tool(description="列出草稿")
    @async_run
    @guard(ctx)
    def list_drafts() -> dict[str, Any]:
        return svc().list_drafts()
