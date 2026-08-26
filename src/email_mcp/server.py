from __future__ import annotations

import argparse
import logging

from mcp.server.fastmcp import FastMCP

from email_mcp.config import http_token, load_account
from email_mcp.context import AppContext
from email_mcp.provider.imap_provider import ImapProvider
from email_mcp.tools import (
    action_tools,
    advanced_tools,
    config_tools,
    read_tools,
    send_tools,
)

logger = logging.getLogger(__name__)


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
    config_tools.register(mcp, ctx)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="email-mcp server")
    parser.add_argument("--http", action="store_true", help="以 Streamable HTTP 模式运行")
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="HTTP 监听地址（默认 127.0.0.1；公网部署用 0.0.0.0）",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="HTTP 监听端口（默认 8080）"
    )
    args = parser.parse_args()

    account = load_account(strict=False)
    if account is None:
        logger.warning(
            "未检测到邮箱配置（.env），服务以未配置状态启动；"
            "agent 可通过 get_account_status 查看状态、configure_account 完成配置"
        )
    ctx = AppContext(account=account, provider=ImapProvider())
    mcp = build_server(ctx, host=args.host, port=args.port)

    ctx.start_scheduler()
    try:
        if args.http:
            token = http_token()
            if token:
                logger.warning(
                    "EMAIL_HTTP_TOKEN 已设置，但当前 mcp 版本不支持静态 Bearer 认证，"
                    "该 token 不会被校验；请仅在受信任的本地/反向代理环境暴露此服务"
                )
            # mcp 1.29.1 的 FastMCP.run() 只接受 transport/mount_path：
            # - HTTP 传输的合法取值是 "streamable-http"（"http" 会抛 ValueError）
            # - host/port 已在 build_server 构造 FastMCP 时传入
            mcp.run(transport="streamable-http")
        else:
            mcp.run(transport="stdio")
    finally:
        if ctx.scheduler is not None:
            ctx.scheduler.stop()


if __name__ == "__main__":
    main()
