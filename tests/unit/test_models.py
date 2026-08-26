from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from email_mcp.models import Account, AttachmentMeta, EmailAddress, EmailMessage


def test_email_address_requires_email():
    addr = EmailAddress(email="a@b.com")
    assert addr.email == "a@b.com"
    assert addr.name is None


def test_email_message_defaults():
    msg = EmailMessage(
        id="INBOX:42",
        account_id="default",
        folder="INBOX",
        subject="Hi",
        from_=EmailAddress(email="x@y.com"),
        to=[EmailAddress(email="me@y.com")],
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        body="hello",
    )
    assert msg.cc == []
    assert msg.flags == []
    assert msg.attachments == []
    assert msg.body_html is None
    assert msg.message_id == ""


def test_attachment_meta_fields():
    a = AttachmentMeta(filename="a.pdf", size=10, mime_type="application/pdf", part_id="1")
    assert a.part_id == "1"


def test_account_requires_hosts():
    with pytest.raises(ValidationError):
        Account(imap_host="", smtp_host="", username="u@x.com")


def test_account_auth_mode_enum():
    with pytest.raises(ValidationError):
        Account(
            imap_host="imap", smtp_host="smtp", username="u@x.com",
            auth_mode="unknown",
        )
