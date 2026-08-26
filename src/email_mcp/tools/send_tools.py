from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册发送/草稿组工具。"""
    # AppContext.__post_init__ 总会创建 EmailService；assert 收窄 Optional 字段以满足 mypy strict
    assert ctx.email_service is not None
    svc = ctx.email_service

    @mcp.tool(description="直接发送邮件（立即投递）；to 为收件人地址列表")
    def send_email(
        to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any]:
        return svc.send_email(to=to, cc=cc, subject=subject, body=body)

    @mcp.tool(description="存草稿到 Drafts 文件夹（人工确认后手动发送）；to 可为空")
    def save_draft(
        to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict[str, Any]:
        return svc.save_draft(to=to, cc=cc, subject=subject, body=body)

    @mcp.tool(description="列出草稿")
    def list_drafts() -> dict[str, Any]:
        return svc.list_drafts()
