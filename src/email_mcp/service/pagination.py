"""分页工具：参数校验与分页元数据计算。

约定（与 EmailProvider 协议一致）：provider 负责按 page/page_size 过滤与
切片；服务层只做参数校验，并根据 provider 返回的 total 计算分页元数据，
不得对已切片的列表再次分页。

空列表约定：total == 0 时 total_pages 为 0。客户端不要用 total_pages 来
界定首页请求——空收件箱的第一页请求仍是合法的（返回空 items）。
"""
from __future__ import annotations

from dataclasses import dataclass

from email_mcp.errors import EmailMCPError, ErrorCode

MAX_PAGE_SIZE = 100


@dataclass
class PageMeta:
    """一页数据的元信息（不含数据本身）。"""

    total: int
    page: int
    page_size: int
    total_pages: int


def validate_page_params(page: int, page_size: int) -> None:
    """校验分页参数，非法时抛 CONFIG_INVALID。"""
    if page < 1:
        raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"页码必须 ≥ 1，收到 {page}")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID,
            f"page_size 必须在 1-{MAX_PAGE_SIZE} 之间，收到 {page_size}",
        )


def page_meta(total: int, page: int, page_size: int) -> PageMeta:
    """按 provider 过滤后的总数计算分页元数据（不做切片）。"""
    validate_page_params(page, page_size)
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PageMeta(total=total, page=page, page_size=page_size, total_pages=total_pages)
