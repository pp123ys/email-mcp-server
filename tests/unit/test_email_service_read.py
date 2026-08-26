from email_mcp.errors import ErrorCode
from email_mcp.service.email_service import EmailService


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_list_inbox_paginated(account, provider):
    svc = make_service(account, provider)
    result = svc.list_inbox(page=1, page_size=2)
    assert result["success"] is True
    data = result["data"]
    assert data["total"] == 3
    assert [m["subject"] for m in data["items"]] == ["s1", "s2"]


def test_list_inbox_unread_filter(account, provider):
    svc = make_service(account, provider)
    data = svc.list_inbox(page=1, page_size=10, unread_only=True)["data"]
    assert data["total"] == 1
    assert data["items"][0]["subject"] == "s2"


def test_list_inbox_from_filter(account, provider):
    svc = make_service(account, provider)
    data = svc.list_inbox(page=1, page_size=10, from_email="boss@x.com")["data"]
    assert data["total"] == 1


def test_read_email_returns_message(account, provider):
    svc = make_service(account, provider)
    result = svc.read_email("INBOX:1")
    assert result["success"] is True
    assert result["data"]["subject"] == "s1"


def test_read_email_missing_returns_error(account, provider):
    svc = make_service(account, provider)
    result = svc.read_email("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.EMAIL_NOT_FOUND


def test_parse_email_id_splits_on_last_colon(account, provider):
    svc = make_service(account, provider)
    assert svc._parse_email_id("INBOX:7") == ("INBOX", "7")
    assert svc._parse_email_id("My Folder:Sub:8") == ("My Folder:Sub", "8")


def test_invalid_email_id(account, provider):
    svc = make_service(account, provider)
    result = svc.read_email("no-colon-here")
    assert result["error"]["code"] == ErrorCode.CONFIG_INVALID


def test_get_account_info_hides_secret(account, provider):
    svc = make_service(account, provider)
    data = svc.get_account_info()["data"]
    assert data["username"] == "me@test.local"
    assert "auth_secret" not in data
    assert "s3cret" not in str(data)


def test_search_emails(account, provider):
    svc = make_service(account, provider)
    data = svc.search_emails(query="s2")["data"]
    assert [m["subject"] for m in data] == ["s2"]


def test_unexpected_exception_sealed_as_internal(account, provider, monkeypatch):
    def boom(self, account, folder, *, page, page_size, unread_only=False, from_email=None):
        raise RuntimeError("boom")

    # 类级 patch：实例级 setattr 会使普通函数失去绑定，调用时先抛 TypeError
    monkeypatch.setattr(type(provider), "list_messages", boom)
    svc = make_service(account, provider)
    result = svc.list_inbox(page=1, page_size=10)
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.INTERNAL


def test_wrap_redacts_account_secret(account, provider, monkeypatch):
    def boom(self, account, folder, *, page, page_size, unread_only=False, from_email=None):
        raise RuntimeError(f"leaked {account.auth_secret} in imap error")

    monkeypatch.setattr(type(provider), "list_messages", boom)
    svc = make_service(account, provider)
    result = svc.list_inbox(page=1, page_size=10)
    assert result["success"] is False
    assert "s3cret-not-in-logs" not in str(result)
    assert "***" in str(result)
