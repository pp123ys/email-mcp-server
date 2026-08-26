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
