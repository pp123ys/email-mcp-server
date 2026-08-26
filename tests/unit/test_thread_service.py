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


def test_get_thread_empty_message_id_seed(account, provider):
    # 邮件无 Message-ID 头 → seed.message_id 为空串；
    # FakeProvider.get_thread("") 返回空列表，服务返回 success: True + 空 data
    from datetime import datetime, timezone

    from email_mcp.models import EmailAddress, EmailMessage

    msg = EmailMessage(
        id="INBOX:1",
        account_id="default",
        folder="INBOX",
        subject="no-mid",
        from_=EmailAddress(email="a@x.com"),
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        body="x",
        message_id="",
    )
    provider.messages = [msg]
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:1")
    assert result["success"] is True
    assert result["data"] == []


def test_get_thread_get_message_exception_sealed(account, provider, monkeypatch):
    def boom(self, account, folder, uid):
        raise RuntimeError("imap boom")

    monkeypatch.setattr(type(provider), "get_message", boom)
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == "INTERNAL"


def test_get_thread_provider_error_sealed(account, provider, monkeypatch):
    def boom(self, account, message_id):
        raise RuntimeError("thread boom")

    monkeypatch.setattr(type(provider), "get_thread", boom)
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == "INTERNAL"
