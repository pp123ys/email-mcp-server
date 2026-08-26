from email_mcp.service.thread_service import ThreadService
from tests.unit.fakes import make_message


def test_get_thread_resolves_ancestors_and_descendants(account, provider):
    provider.messages = [
        make_message(uid=1, message_id="root@x.com", subject="hello"),
        make_message(
            uid=2, message_id="reply1@x.com", subject="Re: hello", in_reply_to="root@x.com"
        ),
        make_message(
            uid=3, message_id="reply2@x.com", subject="Re: hello", in_reply_to="reply1@x.com"
        ),
        make_message(uid=4, message_id="other@x.com", subject="unrelated"),
    ]
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:2")  # 种子 reply1
    assert result["success"] is True
    ids = {m["message_id"] for m in result["data"]}
    assert ids == {"root@x.com", "reply1@x.com", "reply2@x.com"}


def test_get_thread_seed_alone_returns_singleton(account, provider):
    provider.messages = [
        make_message(uid=1, message_id="lone@x.com", subject="lone"),
        make_message(uid=2, message_id="other@x.com", subject="unrelated"),
    ]
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:1")
    assert len(result["data"]) == 1
    assert result["data"][0]["message_id"] == "lone@x.com"


def test_get_thread_missing_message(account, provider):
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == "EMAIL_NOT_FOUND"


def test_get_thread_invalid_email_id(account, provider):
    svc = ThreadService(provider, account)
    assert svc.get_thread("no-colon-here")["error"]["code"] == "CONFIG_INVALID"
    assert svc.get_thread("INBOX:")["error"]["code"] == "CONFIG_INVALID"
    assert svc.get_thread(":1")["error"]["code"] == "CONFIG_INVALID"
