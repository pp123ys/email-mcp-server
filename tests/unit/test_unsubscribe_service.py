from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.unsubscribe_service import UnsubscribeService, parse_list_unsubscribe


def test_parse_mailto_header():
    header = "<mailto:unsub@news.com?subject=unsubscribe>, <https://news.com/unsub>"
    assert parse_list_unsubscribe(header) == {
        "mailto": "unsub@news.com",
        "url": "https://news.com/unsub",
    }


def test_parse_absent_header():
    assert parse_list_unsubscribe(None) is None


def test_unsubscribe_without_header_returns_error(account, provider):
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.UNSUBSCRIBE_UNSUPPORTED


def test_unsubscribe_mailto_sends(account, provider):
    provider.messages[0].headers = {
        "List-Unsubscribe": "<mailto:unsub@news.com?subject=unsubscribe>"
    }
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is True
    assert result["data"]["unsubscribed_to"] == "unsub@news.com"
    assert provider.sent[0]["to"] == ["unsub@news.com"]


def test_unsubscribe_missing_message(account, provider):
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.EMAIL_NOT_FOUND


def test_unsubscribe_invalid_email_id(account, provider):
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("no-colon-here")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.CONFIG_INVALID


def test_unsubscribe_case_insensitive_header(account, provider):
    provider.messages[0].headers = {"list-unsubscribe": "<mailto:unsub@news.com>"}
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is True
    assert result["data"]["unsubscribed_to"] == "unsub@news.com"


def test_unsubscribe_url_only_header(account, provider):
    provider.messages[0].headers = {"List-Unsubscribe": "<https://news.com/unsub>"}
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.UNSUBSCRIBE_UNSUPPORTED


def test_unsubscribe_send_error_preserves_code(account, provider, monkeypatch):
    def boom(self, account, *, to, cc=None, subject, body):
        raise EmailMCPError(ErrorCode.SMTP_AUTH_FAILED, "smtp auth failed")

    monkeypatch.setattr(type(provider), "send", boom)
    provider.messages[0].headers = {"List-Unsubscribe": "<mailto:unsub@news.com>"}
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["error"]["code"] == ErrorCode.SMTP_AUTH_FAILED


def test_unsubscribe_get_headers_error_preserves_code(account, provider, monkeypatch):
    def boom(self, account, folder, uid):
        raise EmailMCPError(ErrorCode.IMAP_AUTH_FAILED, "imap auth failed")

    monkeypatch.setattr(type(provider), "get_headers", boom)
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.IMAP_AUTH_FAILED


def test_unsubscribe_get_headers_unexpected_exception_sealed(account, provider, monkeypatch):
    def boom(self, account, folder, uid):
        raise RuntimeError("imap boom")

    monkeypatch.setattr(type(provider), "get_headers", boom)
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.INTERNAL


def test_unsubscribe_invalid_mailto_recipient(account, provider):
    # mailto 不是合法邮箱 → validate_recipients 抛 INVALID_RECIPIENT，错误直传
    provider.messages[0].headers = {"List-Unsubscribe": "<mailto:not-an-email>"}
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.INVALID_RECIPIENT
    assert provider.sent == []


def test_unsubscribe_send_unexpected_exception_sealed(account, provider, monkeypatch):
    def boom(self, account, *, to, cc=None, subject, body):
        raise RuntimeError("smtp boom")

    monkeypatch.setattr(type(provider), "send", boom)
    provider.messages[0].headers = {"List-Unsubscribe": "<mailto:unsub@news.com>"}
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.INTERNAL
