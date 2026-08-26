"""验证 ImapProvider 用 mock 的 IMAP 连接执行正确协议序列。"""
from unittest.mock import MagicMock, patch

from email_mcp.provider.imap_provider import ImapProvider

RAW = (
    b"From: Sender <sender@x.com>\r\nTo: me@x.com\r\nSubject: Hello\r\n"
    b"Message-ID: <m1@x.com>\r\nDate: Thu, 01 Jan 2026 10:00:00 +0000\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n\r\nplain body"
)


def test_list_messages_selects_inbox_and_fetches(account):
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b"1"])
    conn.fetch.return_value = ("OK", [(b"1 (RFC822 {38}", RAW, b")")])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        provider = ImapProvider()
        msgs, total = provider.list_messages(account, "INBOX", page=1, page_size=10)
    assert total == 1
    assert msgs[0].subject == "Hello"
    conn.select.assert_called_once_with("INBOX", readonly=True)


def test_get_message_missing_raises_keyerror(account):
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.fetch.return_value = ("BAD", [])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        provider = ImapProvider()
        try:
            provider.get_message(account, "INBOX", "999")
            raise AssertionError("should have raised KeyError")
        except KeyError:
            pass


def test_get_thread_expands_chain(account):
    raw_root = (
        b"From: a@x.com\r\nTo: me@x.com\r\nSubject: root\r\nMessage-ID: <r@x.com>\r\n"
        b"Date: Thu, 01 Jan 2026 10:00:00 +0000\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nroot"
    )
    raw_reply = (
        b"From: b@x.com\r\nTo: me@x.com\r\nSubject: Re: root\r\nMessage-ID: <p@x.com>\r\n"
        b"In-Reply-To: <r@x.com>\r\nDate: Thu, 01 Jan 2026 11:00:00 +0000\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nreply"
    )
    by_uid = {b"1": raw_root, b"2": raw_reply}
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"2"])

    def fake_search(*args):
        if "Message-ID" in args:
            return ("OK", [b"1"])
        if "In-Reply-To" in args:
            return ("OK", [b"2"])
        return ("OK", [b""])

    def fake_fetch(uid, *args):
        raw = by_uid.get(uid)
        if raw is None:
            return ("OK", [b""])
        return ("OK", [(uid, raw, b")")])

    conn.search.side_effect = fake_search
    conn.fetch.side_effect = fake_fetch
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        provider = ImapProvider()
        thread = provider.get_thread(account, "<r@x.com>")
    ids = {m.message_id for m in thread}
    assert ids == {"<r@x.com>", "<p@x.com>"}


def test_download_attachment_returns_payload(account):
    raw = (
        b"From: a@x.com\r\nTo: me@x.com\r\nSubject: att\r\n"
        b"Content-Type: multipart/mixed; boundary=bb\r\n\r\n"
        b"--bb\r\nContent-Type: text/plain\r\n\r\nhello\r\n"
        b"--bb\r\nContent-Type: application/pdf; name=\"doc.pdf\"\r\n"
        b"Content-Disposition: attachment; filename=\"doc.pdf\"\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\n"
        b"aGVsbG8=\r\n"
        b"--bb--\r\n"
    )
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.fetch.return_value = ("OK", [(b"1 (RFC822 {38}", raw, b")")])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        provider = ImapProvider()
        content = provider.download_attachment(account, "INBOX", "1", "2")
    assert content == b"hello"


def test_get_thread_resolves_ancestors_from_reply_seed(account):
    raw_root = (
        b"From: a@x.com\r\nTo: me@x.com\r\nSubject: root\r\nMessage-ID: <r@x.com>\r\n"
        b"Date: Thu, 01 Jan 2026 10:00:00 +0000\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nroot"
    )
    raw_reply = (
        b"From: b@x.com\r\nTo: me@x.com\r\nSubject: Re: root\r\nMessage-ID: <p@x.com>\r\n"
        b"In-Reply-To: <r@x.com>\r\nDate: Thu, 01 Jan 2026 11:00:00 +0000\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nreply"
    )
    by_uid = {b"1": raw_root, b"2": raw_reply}
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"2"])

    def fake_search(*args):
        quoted = args[-1] if args else ""
        mid = quoted.strip('"')
        if mid == "<p@x.com>":
            return ("OK", [b"2"])  # 种子（回复）的 Message-ID
        if mid == "<r@x.com>":
            return ("OK", [b"1"])  # 祖先的 Message-ID
        return ("OK", [b""])

    def fake_fetch(uid, *args):
        raw = by_uid.get(uid)
        if raw is None:
            return ("OK", [b""])
        return ("OK", [(uid, raw, b")")])

    conn.search.side_effect = fake_search
    conn.fetch.side_effect = fake_fetch
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        provider = ImapProvider()
        thread = provider.get_thread(account, "<p@x.com>")  # 种子是回复
    ids = {m.message_id for m in thread}
    assert ids == {"<r@x.com>", "<p@x.com>"}
