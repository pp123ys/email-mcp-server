from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext
from email_mcp.service.email_service import EmailService
from email_mcp.tools._guard import async_run, guard


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册操作组工具。"""
    # 服务在 configure_account 热重载时重建，须每次调用时从 ctx 取当前实例
    def svc() -> EmailService:
        assert ctx.email_service is not None
        return ctx.email_service

    @mcp.tool(
        description=(
            "回复邮件：自动生成引用块并填收件人；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def reply_email(email_id: str, body: str, cc: list[str] | None = None) -> dict[str, Any]:
        return svc().reply_email(email_id, body, cc)

    @mcp.tool(
        description=(
            "转发邮件：自动生成引用块；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def forward_email(email_id: str, to: list[str], body: str) -> dict[str, Any]:
        return svc().forward_email(email_id, to, body)

    @mcp.tool(description="标记已读；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def mark_read(email_id: str) -> dict[str, Any]:
        return svc().mark_read(email_id)

    @mcp.tool(description="标记未读；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def mark_unread(email_id: str) -> dict[str, Any]:
        return svc().mark_unread(email_id)

    @mcp.tool(description="归档（移入 All Mail）；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def archive(email_id: str) -> dict[str, Any]:
        return svc().archive(email_id)

    @mcp.tool(description="移动到指定文件夹；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def move_email(email_id: str, dest_folder: str) -> dict[str, Any]:
        return svc().move_email(email_id, dest_folder)

    @mcp.tool(description="移入废纸篓（软删除）；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def trash_email(email_id: str) -> dict[str, Any]:
        return svc().trash_email(email_id)

    @mcp.tool(
        description=(
            "设置邮件标记（默认星标 \\Flagged）；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def set_flag(email_id: str, flag: str = "\\Flagged") -> dict[str, Any]:
        return svc().set_flag(email_id, flag)

    @mcp.tool(description="置顶/星标邮件；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def pin_email(email_id: str) -> dict[str, Any]:
        return svc().pin_email(email_id)

    @mcp.tool(
        description=(
            "延后提醒（until 为 ISO 时间，到期重新标记未读）；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def snooze_email(email_id: str, until: str) -> dict[str, Any]:
        return svc().snooze_email(email_id, until)
