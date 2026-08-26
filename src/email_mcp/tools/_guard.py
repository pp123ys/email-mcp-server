"""邮箱工具未配置守卫。"""
from __future__ import annotations

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
