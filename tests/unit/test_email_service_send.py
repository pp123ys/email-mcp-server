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
