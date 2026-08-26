from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

from email_mcp.config import load_account
from email_mcp.context import AppContext
from email_mcp.provider.imap_provider import ImapProvider
from email_mcp.tools import action_tools, advanced_tools, read_tools, send_tools


def build_server(ctx: AppContext, *, host: str = "127.0.0.1", port: int = 8080) -> FastMCP:
    """构建 MCP 服务器并注册工具。

    mcp 1.29.1 的 FastMCP.run() 不接受 host/port，HTTP 传输的实际
    绑定地址/端口必须在构造 FastMCP 时传入（此处为 build_server 参数）。
    """
    mcp = FastMCP("email-mcp", host=host, port=port)
    read_tools.register(mcp, ctx)
    send_tools.register(mcp, ctx)
    action_tools.register(mcp, ctx)
    advanced_tools.register(mcp, ctx)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="email-mcp server")
    parser.add_argument("--http", action="store_true", help="以 Streamable HTTP 模式运行")
    args = parser.parse_args()

    account = load_account()
    ctx = AppContext(account=account, provider=ImapProvider())
    mcp = build_server(ctx)

    scheduler = ctx.scheduler
    assert scheduler is not None  # AppContext.__post_init__ 总会创建 Scheduler
    scheduler.start()
    try:
        if args.http:
            # mcp 1.29.1 的 FastMCP.run() 只接受 transport/mount_path：
            # - HTTP 传输的合法取值是 "streamable-http"（"http" 会抛 ValueError）
            # - host/port 已在 build_server 构造 FastMCP 时传入
            # - 1.29.1 无 auth_token 参数（无静态 Bearer token 支持；
            #   服务只绑定 127.0.0.1，需要认证时由反向代理层处理）
            mcp.run(transport="streamable-http")
        else:
            mcp.run(transport="stdio")
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
