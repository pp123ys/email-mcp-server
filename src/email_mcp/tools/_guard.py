"""邮箱工具未配置守卫与异步化包装。"""
from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, TypeVar

from email_mcp.context import AppContext
from email_mcp.errors import ErrorCode, error_result

T = TypeVar("T", bound=Callable[..., Any])

CONFIG_MISSING_RESPONSE = error_result(
    ErrorCode.CONFIG_MISSING,
    "邮箱尚未配置。请先调用 get_account_status 查看缺失配置，"
    "再调用 configure_account 完成配置（配置前请先向用户确认凭据）。",
)


def async_run(fn: T) -> T:
    """把同步工具函数包装为 async：经 asyncio.to_thread 在线程池执行。

    修复：FastMCP 对同步工具直接在事件循环线程执行，阻塞的 IMAP/SMTP 调用
    会卡死整个 asyncio 事件循环（其他请求全部排队）。包装后事件循环不被阻塞。
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(fn, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


def guard(ctx: AppContext) -> Callable[[T], T]:
    """装饰器：包装 MCP 工具函数，未配置时直接返回 CONFIG_MISSING 引导响应。"""

    def deco(fn: T) -> T:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not ctx.configured:
                return CONFIG_MISSING_RESPONSE
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return deco
