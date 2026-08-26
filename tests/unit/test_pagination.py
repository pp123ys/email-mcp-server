import pytest

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.pagination import PageMeta, page_meta, validate_page_params


def test_page_meta_non_exact_multiple():
    m = page_meta(total=25, page=1, page_size=10)
    assert m == PageMeta(total=25, page=1, page_size=10, total_pages=3)


def test_page_meta_exact_multiple():
    m = page_meta(total=20, page=2, page_size=10)
    assert m.total_pages == 2


def test_page_meta_empty_total():
    m = page_meta(total=0, page=1, page_size=10)
    assert m.total_pages == 0
    assert m.total == 0


def test_validate_rejects_page_zero():
    with pytest.raises(EmailMCPError) as ei:
        validate_page_params(page=0, page_size=10)
    assert ei.value.code == ErrorCode.CONFIG_INVALID


def test_validate_rejects_oversized_page_size():
    with pytest.raises(EmailMCPError) as ei:
        validate_page_params(page=1, page_size=101)
    assert ei.value.code == ErrorCode.CONFIG_INVALID


def test_validate_rejects_zero_and_negative_page_size():
    with pytest.raises(EmailMCPError):
        validate_page_params(page=1, page_size=0)
    with pytest.raises(EmailMCPError):
        validate_page_params(page=1, page_size=-5)


def test_validate_accepts_max_boundary():
    validate_page_params(page=1, page_size=100)  # 不抛即通过


def test_page_meta_validates_before_computing():
    with pytest.raises(EmailMCPError):
        page_meta(total=25, page=0, page_size=10)
