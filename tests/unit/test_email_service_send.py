from email_mcp.service.email_service import EmailService


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_send_email(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=["a@b.com"], subject="Hi", body="Hello")
    assert result["success"] is True
    assert result["data"]["message_id"].startswith("sent-")
    assert provider.sent[0]["subject"] == "Hi"


def test_send_email_rejects_invalid_recipient(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=["not-an-email"], subject="Hi", body="Hello")
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_RECIPIENT"
    assert provider.sent == []


def test_save_draft_goes_to_drafts(account, provider):
    svc = make_service(account, provider)
    result = svc.save_draft(to=["a@b.com"], subject="Draft", body="WIP")
    assert result["success"] is True
    assert result["data"]["draft_id"].startswith("Drafts:")
    assert len(provider.drafts) == 1


def test_list_drafts(account, provider):
    svc = make_service(account, provider)
    svc.save_draft(to=["a@b.com"], subject="Draft", body="WIP")
    data = svc.list_drafts()["data"]
    assert len(data) == 1
    assert data[0]["subject"] == "Draft"


def test_send_email_rejects_empty_to(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=[], subject="Hi", body="Hello")
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_RECIPIENT"
    assert provider.sent == []


def test_send_email_cc_forwarded(account, provider):
    svc = make_service(account, provider)
    svc.send_email(to=["a@b.com"], cc=["c@d.com"], subject="Hi", body="Hello")
    assert provider.sent[0]["cc"] == ["c@d.com"]


def test_send_email_rejects_invalid_cc(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=["a@b.com"], cc=["bad-cc"], subject="Hi", body="Hello")
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_RECIPIENT"
    assert provider.sent == []


def test_send_email_aggregates_multiple_invalid(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=["bad1", "bad2"], subject="Hi", body="Hello")
    assert result["error"]["code"] == "INVALID_RECIPIENT"


def test_save_draft_allows_empty_to(account, provider):
    svc = make_service(account, provider)
    result = svc.save_draft(to=[], subject="Untitled", body="WIP")
    assert result["success"] is True


def test_send_email_rate_limited(account, provider):
    from email_mcp.service.guardrails import RateLimiter

    svc = EmailService(
        provider=provider,
        account=account,
        rate_limiter=RateLimiter(max_per_minute=1),
    )
    assert svc.send_email(to=["a@b.com"], subject="Hi", body="1")["success"] is True
    result = svc.send_email(to=["a@b.com"], subject="Hi", body="2")
    assert result["success"] is False
    assert result["error"]["code"] == "RATE_LIMITED"
