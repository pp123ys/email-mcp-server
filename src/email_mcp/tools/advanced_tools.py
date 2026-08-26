from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册高级组工具。"""
    # AppContext.__post_init__ 总会创建这两个服务；assert 收窄 Optional 字段以满足 mypy strict
    assert ctx.email_service is not None
    assert ctx.unsubscribe_service is not None
    svc = ctx.email_service
    unsub = ctx.unsubscribe_service

    @mcp.tool(
        description=(
            "基于 List-Unsubscribe 头自动退订（仅 mailto 方式）；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    def unsubscribe(email_id: str) -> dict[str, Any]:
        return unsub.unsubscribe(email_id)

    @mcp.tool(
        description=(
            "定时发送（send_at 为 ISO 时间，服务器进程存活期间到期执行）；"
            "to 不能为空"
        )
    )
    def schedule_send(to: list[str], subject: str, body: str, send_at: str) -> dict[str, Any]:
        return svc.schedule_send(to=to, subject=subject, body=body, send_at=send_at)

    @mcp.tool(
        description=(
            "同模板批量发送（每批最多 20 封，受发送频率限制）；"
            "to 不能为空"
        )
    )
    def batch_send(to: list[str], subject: str, body: str) -> dict[str, Any]:
        return svc.batch_send(to=to, subject=subject, body=body)

    @mcp.tool(description="创建标签（IMAP 映射为文件夹）")
    def create_label(name: str) -> dict[str, Any]:
        return svc.create_label(name)

    @mcp.tool(description="标签管理：action=list 列出，action=delete 删除（需 name）")
    def manage_labels(action: str, name: str | None = None) -> dict[str, Any]:
        return svc.manage_labels(action=action, name=name)
