from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from email_mcp.errors import EmailMCPError, ErrorCode

T = TypeVar("T")

MAX_PAGE_SIZE = 100


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate(items: list[T], *, page: int, page_size: int) -> Page[T]:
    """对列表分页。page 从 1 开始；越界页返回空 items 但保留 total。"""
    if page < 1:
        raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"页码必须 ≥ 1，收到 {page}")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID, f"page_size 必须在 1-{MAX_PAGE_SIZE} 之间，收到 {page_size}"
        )
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    return Page(
        items=items[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
