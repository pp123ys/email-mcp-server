from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册发送/草稿组工具（Task 19 填充）。"""
