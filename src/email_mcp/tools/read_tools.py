from mcp.server.fastmcp import FastMCP

from email_mcp.context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    """注册读取组工具（Task 18 填充）。"""
