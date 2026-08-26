import pytest

from email_mcp.models import Account
from tests.unit.fakes import FakeProvider, make_message


@pytest.fixture
def account() -> Account:
    return Account(
        imap_host="imap.test.local",
        smtp_host="smtp.test.local",
        username="me@test.local",
        auth_secret="s3cret-not-in-logs",
    )


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider(
        [
            make_message(uid=1, subject="s1", read=True),
            make_message(uid=2, subject="s2", read=False),
            make_message(uid=3, subject="s3", read=True, from_addr="boss@x.com"),
        ]
    )
