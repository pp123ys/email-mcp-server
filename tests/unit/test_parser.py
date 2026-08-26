from email_mcp.provider.parser import find_part_by_path, parse_email_message

RAW = (
    b"From: Sender <sender@x.com>\r\n"
    b"To: me@x.com\r\n"
    b"Subject: Hello\r\n"
    b"Message-ID: <m1@x.com>\r\n"
    b"Date: Thu, 01 Jan 2026 10:00:00 +0000\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"plain body here"
)


def test_parse_basic_message():
    msg = parse_email_message(RAW, folder="INBOX", uid="42")
    assert msg.id == "INBOX:42"
    assert msg.subject == "Hello"
    assert msg.from_.email == "sender@x.com"
    assert msg.body == "plain body here"
    assert msg.message_id == "<m1@x.com>"
    assert msg.headers["Subject"] == "Hello"


def test_parse_html_message_falls_back_to_stripped_text():
    raw = (
        b"From: a@b.com\r\nTo: me@x.com\r\nSubject: Html\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n\r\n"
        b"<html><body><p>Hello <b>world</b></p></body></html>"
    )
    msg = parse_email_message(raw, folder="INBOX", uid="1")
    assert "world" in msg.body
    assert "<" not in msg.body


def test_parse_multipart_attachment_path():
    raw = (
        b"From: a@b.com\r\nTo: me@x.com\r\nSubject: Multipart\r\n"
        b"Content-Type: multipart/mixed; boundary=bb\r\n\r\n"
        b"--bb\r\nContent-Type: text/plain\r\n\r\nhello\r\n"
        b"--bb\r\nContent-Type: application/pdf; name=\"doc.pdf\"\r\n"
        b"Content-Disposition: attachment; filename=\"doc.pdf\"\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\n"
        b"aGVsbG8=\r\n"
        b"--bb--\r\n"
    )
    msg = parse_email_message(raw, folder="INBOX", uid="1")
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename == "doc.pdf"
    assert msg.attachments[0].part_id == "2"


def test_parse_nested_multipart_attachment_path():
    raw = (
        b"From: a@b.com\r\nTo: me@x.com\r\nSubject: Nested\r\n"
        b"Content-Type: multipart/mixed; boundary=o\r\n\r\n"
        b"--o\r\nContent-Type: multipart/alternative; boundary=i\r\n\r\n"
        b"--i\r\nContent-Type: text/plain\r\n\r\nhi\r\n"
        b"--i--\r\n"
        b"--o\r\nContent-Type: multipart/related; boundary=r\r\n\r\n"
        b"--r\r\nContent-Type: text/html\r\n\r\n<html></html>\r\n"
        b"--r\r\nContent-Type: image/png; name=\"img.png\"\r\n"
        b"Content-Disposition: attachment; filename=\"img.png\"\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\n"
        b"aGk=\r\n"
        b"--r--\r\n"
        b"--o--\r\n"
    )
    msg = parse_email_message(raw, folder="INBOX", uid="1")
    assert len(msg.attachments) == 1
    assert msg.attachments[0].part_id == "2.2"


def test_find_part_by_path():
    raw = (
        b"From: a@b.com\r\nTo: me@x.com\r\nSubject: Multipart\r\n"
        b"Content-Type: multipart/mixed; boundary=bb\r\n\r\n"
        b"--bb\r\nContent-Type: text/plain\r\n\r\nhello\r\n"
        b"--bb\r\nContent-Type: application/pdf; name=\"doc.pdf\"\r\n"
        b"Content-Disposition: attachment; filename=\"doc.pdf\"\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\n"
        b"aGVsbG8=\r\n"
        b"--bb--\r\n"
    )
    import email
    from email import policy

    msg = email.message_from_bytes(raw, policy=policy.default)
    part = find_part_by_path(msg, (2,))
    assert part is not None
    assert part.get_filename() == "doc.pdf"
    assert find_part_by_path(msg, (9, 9)) is None


def test_parse_body_skips_attachment_text():
    raw = (
        b"From: a@b.com\r\nTo: me@x.com\r\nSubject: Att\r\n"
        b"Content-Type: multipart/mixed; boundary=bb\r\n\r\n"
        b"--bb\r\nContent-Type: text/html\r\n\r\n<html><body><p>Hello</p></body></html>\r\n"
        b"--bb\r\nContent-Type: text/plain; name=\"notes.txt\"\r\n"
        b"Content-Disposition: attachment; filename=\"notes.txt\"\r\n\r\n"
        b"attachment content, not body\r\n"
        b"--bb--\r\n"
    )
    msg = parse_email_message(raw, folder="INBOX", uid="1")
    assert "attachment content" not in msg.body
    assert "Hello" in msg.body


def test_parse_missing_date_is_aware():
    raw = b"From: a@b.com\r\nTo: me@x.com\r\nSubject: no date\r\n\r\nbody"
    msg = parse_email_message(raw, folder="INBOX", uid="1")
    assert msg.date.tzinfo is not None
