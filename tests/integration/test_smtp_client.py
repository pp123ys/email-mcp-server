import smtplib
from unittest.mock import MagicMock, patch

import pytest

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.provider.smtp_client import SMTPClient


def test_send_message(account):
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn) as cls:
        SMTPClient(account).send(
            to=["a@b.com", "c@d.com"],
            cc=None,
            subject="Hi",
            body="Hello",
            sender=account.username,
        )
        cls.assert_called_once()
        conn.login.assert_called_once_with("me@test.local", "s3cret-not-in-logs")
        sent = conn.send_message.call_args.args[0]
        assert sent["Subject"] == "Hi"
        assert sent["To"] == "a@b.com, c@d.com"


def test_auth_failure_raises(account):
    conn = MagicMock()
    conn.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            SMTPClient(account).send(
                to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
            )
    assert ei.value.code == ErrorCode.SMTP_AUTH_FAILED
