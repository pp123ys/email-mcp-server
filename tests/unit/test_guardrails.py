import pytest

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.guardrails import RateLimiter, check_batch_size


def test_batch_within_limit_ok():
    check_batch_size(["a@x.com"] * 5)


def test_batch_over_limit():
    with pytest.raises(EmailMCPError) as ei:
        check_batch_size(["a@x.com"] * 21)
    assert ei.value.code == ErrorCode.BATCH_LIMIT_EXCEEDED


def test_rate_limiter_allows_until_limit():
    rl = RateLimiter(max_per_minute=3)
    rl.check()
    rl.check()
    rl.check()


def test_rate_limiter_rejects_over_limit():
    rl = RateLimiter(max_per_minute=2)
    rl.check()
    rl.check()
    with pytest.raises(EmailMCPError) as ei:
        rl.check()
    assert ei.value.code == ErrorCode.RATE_LIMITED
