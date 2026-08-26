from email_mcp.service.thread_service import ThreadService
from tests.unit.fakes import make_message


def test_get_thread_returns_related_messages(account, provider):
    provider.messages = [
        make_message(uid=1, message_id="t1@x.com", subject="Re: hello"),
        make_message(uid=2, message_id="t1@x.com", subject="Re: hello"),
        make_message(uid=3, message_id="other@x.com", subject="unrelated"),
    ]
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:1")
    assert result["success"] is True
    assert len(result["data"]) == 2


def test_get_thread_missing_message(account, provider):
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == "EMAIL_NOT_FOUND"


def test_get_thread_invalid_email_id(account, provider):
    svc = ThreadService(provider, account)
    result = svc.get_thread("no-colon-here")
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"
