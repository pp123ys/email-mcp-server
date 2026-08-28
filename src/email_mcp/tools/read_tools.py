from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext
from email_mcp.service.email_service import EmailService
from email_mcp.service.thread_service import ThreadService
from email_mcp.tools._guard import async_run, guard


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册读取组工具。"""
    # 服务在 configure_account 热重载时重建，须每次调用时从 ctx 取当前实例
    def svc() -> EmailService:
        assert ctx.email_service is not None
        return ctx.email_service

    def thread() -> ThreadService:
        assert ctx.thread_service is not None
        return ctx.thread_service

    @mcp.tool(description="分页列出邮件，支持未读/发件人/文件夹过滤")
    @async_run
    @guard(ctx)
    def list_inbox(
        folder: str = "INBOX",
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        return svc().list_inbox(
            page=page, page_size=page_size,
            unread_only=unread_only, from_email=from_email, folder=folder,
        )

    @mcp.tool(
        description=(
            "读取单封邮件完整内容（纯文本正文 + 附件元信息）；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def read_email(email_id: str) -> dict[str, Any]:
        return svc().read_email(email_id)

    @mcp.tool(description="拉取整条会话线程；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def get_thread(email_id: str) -> dict[str, Any]:
        return thread().get_thread(email_id)

    @mcp.tool(
        description=(
            "关键词/发件人/日期范围搜索；结果仅含元数据（主题/发件人/日期/ID），"
            "正文为空，需要读取正文请用 read_email"
        )
    )
    @async_run
    @guard(ctx)
    def search_emails(
        query: str = "",
        from_email: str | None = None,
        since: str | None = None,
        until: str | None = None,
        folder: str = "INBOX",
    ) -> dict[str, Any]:
        return svc().search_emails(
            query=query, from_email=from_email, since=since, until=until, folder=folder
        )

    @mcp.tool(description="列出所有文件夹")
    @async_run
    @guard(ctx)
    def list_folders() -> dict[str, Any]:
        return svc().list_folders()

    @mcp.tool(description="列出某邮件的附件元信息；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def get_attachments(email_id: str) -> dict[str, Any]:
        return svc().get_attachments(email_id)

    @mcp.tool(
        description=(
            "按 part_id 下载附件，返回 base64 内容；"
            "email_id 格式为 folder:uid，如 INBOX:1"
        )
    )
    @async_run
    @guard(ctx)
    def download_attachment(email_id: str, part_id: str) -> dict[str, Any]:
        return svc().download_attachment(email_id, part_id)

    @mcp.tool(description="读取原始 RFC 822 邮件头；email_id 格式为 folder:uid，如 INBOX:1")
    @async_run
    @guard(ctx)
    def get_email_headers(email_id: str) -> dict[str, Any]:
        return svc().get_email_headers(email_id)

    @mcp.tool(description="返回当前账号身份信息")
    @async_run
    @guard(ctx)
    def get_account_info() -> dict[str, Any]:
        return svc().get_account_info()
