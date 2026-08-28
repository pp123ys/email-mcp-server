from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext
from email_mcp.service.email_service import EmailService
from email_mcp.service.unsubscribe_service import UnsubscribeService
from email_mcp.tools._guard import async_run, guard


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册高级组工具。"""
    # 服务在 configure_account 热重载时重建，须每次调用时从 ctx 取当前实例
    def svc() -> EmailService:
        assert ctx.email_service is not None
        return ctx.email_service

    def unsub() -> UnsubscribeService:
        assert ctx.unsubscribe_service is not None
        return ctx.unsubscribe_service

    @mcp.tool(
        description=(
            "基于 List-Unsubscribe 头自动退订（仅 mailto 方式）；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def unsubscribe(email_id: str) -> dict[str, Any]:
        return unsub().unsubscribe(email_id)

    @mcp.tool(
        description=(
            "定时发送（send_at 为 ISO 时间，服务器进程存活期间到期执行）；"
            "to 不能为空"
        )
    )
    @async_run
    @guard(ctx)
    def schedule_send(to: list[str], subject: str, body: str, send_at: str) -> dict[str, Any]:
        return svc().schedule_send(to=to, subject=subject, body=body, send_at=send_at)

    @mcp.tool(
        description=(
            "同模板批量发送（每批最多 20 封，受发送频率限制）；"
            "to 不能为空，空 to 拒绝"
        )
    )
    @async_run
    @guard(ctx)
    def batch_send(to: list[str], subject: str, body: str) -> dict[str, Any]:
        return svc().batch_send(to=to, subject=subject, body=body)

    @mcp.tool(description="创建标签（IMAP 映射为文件夹）")
    @async_run
    @guard(ctx)
    def create_label(name: str) -> dict[str, Any]:
        return svc().create_label(name)

    @mcp.tool(description="标签管理：action=list 列出，action=delete 删除（需 name）")
    @async_run
    @guard(ctx)
    def manage_labels(action: str, name: str | None = None) -> dict[str, Any]:
        return svc().manage_labels(action=action, name=name)
