from email_mcp.errors import ErrorCode
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
