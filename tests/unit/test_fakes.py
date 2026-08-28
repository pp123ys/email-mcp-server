import pytest

from email_mcp.models import Account
from tests.unit.fakes import FakeProvider, make_message


def test_make_message_has_folder_uid_id():
    msg = make_message(uid=7, folder="INBOX", subject="t")
    assert msg.id == "INBOX:7"
    assert msg.folder == "INBOX"


def test_fake_list_messages_pagination(account: Account, provider: FakeProvider):
    msgs, total = provider.list_messages(account, "INBOX", page=1, page_size=2)
    assert total == 3
    assert [m.subject for m in msgs] == ["s1", "s2"]


def test_fake_list_messages_unread_filter(account: Account, provider: FakeProvider):
    msgs, total = provider.list_messages(account, "INBOX", page=1, page_size=10, unread_only=True)
    assert total == 1
    assert msgs[0].subject == "s2"


def test_fake_get_message_and_headers(account: Account, provider: FakeProvider):
    msg = provider.get_message(account, "INBOX", "1")
    assert msg.subject == "s1"
    assert provider.get_headers(account, "INBOX", "1")["Subject"] == "s1"


def test_fake_get_message_missing_raises_keyerror(account: Account, provider: FakeProvider):
    with pytest.raises(KeyError):
        provider.get_message(account, "INBOX", "999")


def test_fake_download_attachment_missing_raises_keyerror(
    account: Account, provider: FakeProvider
):
    with pytest.raises(KeyError):
        provider.download_attachment(account, "INBOX", "999", "1")


def test_fake_list_messages_page2_continuation(account: Account, provider: FakeProvider):
    msgs, total = provider.list_messages(account, "INBOX", page=2, page_size=2)
    assert total == 3
    assert [m.subject for m in msgs] == ["s3"]


def test_fake_search_returns_lightweight_text(account: Account, provider: FakeProvider):
    msgs = provider.search(account, query="s2")
    assert len(msgs) == 1
    assert msgs[0].subject == "s2"
    assert msgs[0].body == ""
    assert msgs[0].attachments == []
    # 收件人以元数据形式透传（不随轻量化清空）
    assert msgs[0].to[0].email == "me@x.com"


def test_fake_search_filters_by_query_subject(account: Account, provider: FakeProvider):
    msgs = provider.search(account, query="s2")
    assert [m.subject for m in msgs] == ["s2"]


def test_fake_provider_covers_all_protocol_methods():
    from email_mcp.provider.base import EmailProvider

    protocol_methods = {
        name for name, member in EmailProvider.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    fake_methods = {name for name in vars(FakeProvider) if not name.startswith("_")}
    assert protocol_methods <= fake_methods
