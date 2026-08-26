from unittest.mock import MagicMock, patch

from email_mcp.context import AppContext
from email_mcp.service.config_service import ConfigService


def test_test_email_connection_both_ok(account, provider):
    ctx = AppContext(account=account, provider=provider)
    conn = MagicMock()
    conn.login.return_value = ("OK", [b"logged in"])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
            result = ConfigService(ctx).test_email_connection()
    assert result["success"] is True
    data = result["data"]
    assert data["results"]["imap"]["ok"] is True
    assert data["results"]["smtp"]["ok"] is True


def test_test_email_connection_imap_fails(account, provider):
    ctx = AppContext(account=account, provider=provider)
    with patch(
        "email_mcp.provider.imap_client.imaplib.IMAP4_SSL",
        side_effect=OSError("no route"),
    ):
        with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL") as smtp_cls:
            smtp_conn = MagicMock()
            smtp_conn.login.return_value = (235, b"ok")
            smtp_cls.return_value = smtp_conn
            result = ConfigService(ctx).test_email_connection()
    assert result["data"]["results"]["imap"]["ok"] is False
    assert result["data"]["results"]["smtp"]["ok"] is True
