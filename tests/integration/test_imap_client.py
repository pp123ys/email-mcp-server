import imaplib
import socket
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
    with patch(
        "email_mcp.provider.imap_client.imaplib.IMAP4_SSL",
        side_effect=OSError("no route"),
    ) as cls:
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account, retry_delay_base=0).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_CONNECT_FAILED
    assert cls.call_count == 3  # 首次尝试 + 2 次重试


def test_connect_timeout_maps_to_connection_timeout(account):
    with patch(
        "email_mcp.provider.imap_client.imaplib.IMAP4_SSL",
        side_effect=socket.timeout("timed out"),
    ) as cls:
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account, retry_delay_base=0).connect():
                pass
    assert ei.value.code == ErrorCode.CONNECTION_TIMEOUT
    assert cls.call_count == 3


def test_auth_failure_raises_auth_error(account):
    conn = MagicMock()
    conn.login.side_effect = imaplib.IMAP4.error("auth failed")
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_AUTH_FAILED
    conn.logout.assert_called_once()


def test_yield_body_exception_still_logs_out_and_propagates(account):
    conn = MagicMock()
    conn.login.return_value = ("OK", [b"logged in"])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        client = IMAPClient(account)
        with pytest.raises(RuntimeError, match="boom"):
            with client.connect():
                raise RuntimeError("boom")
    conn.logout.assert_called_once()


def test_login_oserror_maps_to_connect_failed(account):
    conn = MagicMock()
    conn.login.side_effect = OSError("connection reset during login")
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_CONNECT_FAILED
    conn.logout.assert_called_once()
