import imaplib
from unittest.mock import MagicMock, patch

import pytest

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.provider.imap_client import IMAPClient


def test_connect_logs_in_and_out(account):
    conn = MagicMock()
    conn.login.return_value = ("OK", [b"logged in"])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn) as cls:
        client = IMAPClient(account)
        with client.connect() as c:
            assert c is conn
        cls.assert_called_once()
        conn.login.assert_called_once_with("me@test.local", "s3cret-not-in-logs")
        conn.logout.assert_called_once()


def test_connect_failure_raises_connect_error(account):
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", side_effect=OSError("no route")):
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_CONNECT_FAILED


def test_auth_failure_raises_auth_error(account):
    conn = MagicMock()
    conn.login.side_effect = imaplib.IMAP4.error("auth failed")
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_AUTH_FAILED
    conn.logout.assert_called_once()
