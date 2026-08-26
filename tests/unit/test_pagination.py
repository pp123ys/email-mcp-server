import pytest

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.pagination import paginate


def test_page_one():
    p = paginate(list(range(25)), page=1, page_size=10)
    assert p.items == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert p.total == 25
    assert p.page == 1
    assert p.page_size == 10
    assert p.total_pages == 3


def test_page_last_partial():
    p = paginate(list(range(25)), page=3, page_size=10)
    assert p.items == [20, 21, 22, 23, 24]


def test_page_beyond_end_returns_empty():
    p = paginate(list(range(25)), page=9, page_size=10)
    assert p.items == []
    assert p.total == 25


def test_invalid_page_rejected():
    with pytest.raises(EmailMCPError) as ei:
        paginate(list(range(5)), page=0, page_size=10)
    assert ei.value.code == ErrorCode.CONFIG_INVALID


def test_invalid_page_size_rejected():
    with pytest.raises(EmailMCPError):
        paginate(list(range(5)), page=1, page_size=101)
