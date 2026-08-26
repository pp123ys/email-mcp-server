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


def test_send_smtp_exception_maps_to_internal(account):
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    conn.send_message.side_effect = smtplib.SMTPDataError(450, b"try again")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            SMTPClient(account).send(
                to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
            )
    assert ei.value.code == ErrorCode.INTERNAL


def test_send_recipients_refused_maps_to_invalid_recipient(account):
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    conn.send_message.side_effect = smtplib.SMTPRecipientsRefused({"a@b.com": (550, b"rejected")})
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            SMTPClient(account).send(
                to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
            )
    assert ei.value.code == ErrorCode.INVALID_RECIPIENT
    assert ei.value.details["refused"] == {"a@b.com": "(550, b'rejected')"}


def test_send_phase_oserror_maps_to_connect_failed(account):
    conn = MagicMock()
    conn.login.side_effect = OSError("reset during login")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            SMTPClient(account).send(
                to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
            )
    assert ei.value.code == ErrorCode.SMTP_CONNECT_FAILED


def test_send_plain_starttls_branch(account):
    plain = account.model_copy(update={"smtp_ssl": False})
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP", return_value=conn) as cls:
        SMTPClient(plain).send(
            to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
        )
        cls.assert_called_once()
        conn.starttls.assert_called_once()


def test_send_quit_called(account):
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        SMTPClient(account).send(
            to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
        )
    conn.quit.assert_called_once()


def test_send_message_id_is_real_wire_id(account):
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        mid = SMTPClient(account).send(
            to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
        )
    sent = conn.send_message.call_args.args[0]
    assert sent["Message-ID"] == mid
    assert mid.startswith("<") and mid.endswith(">")
