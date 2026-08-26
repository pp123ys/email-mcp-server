from __future__ import annotations

import email
import re
from collections.abc import Iterator
from datetime import datetime
from email import policy
from email.header import decode_header
from email.message import MIMEPart
from email.utils import getaddresses, parsedate_to_datetime

from email_mcp.models import AttachmentMeta, EmailAddress, EmailMessage

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _addresses(value: str | None) -> list[EmailAddress]:
    if not value:
        return []
    return [
        EmailAddress(name=name or None, email=addr)
        for name, addr in getaddresses([value])
        if addr
    ]


def _first_text_plain(part: MIMEPart) -> str:
    if part.is_multipart():
        for sub in part.iter_parts():
            text = _first_text_plain(sub)
            if text:
                return text
        return ""
    if part.get_content_type() == "text/plain":
        return str(part.get_content())
    return ""


def _first_text_html(part: MIMEPart) -> str:
    if part.is_multipart():
        for sub in part.iter_parts():
            html = _first_text_html(sub)
            if html:
                return html
        return ""
    if part.get_content_type() == "text/html":
        return str(part.get_content())
    return ""


def _strip_html(html: str) -> str:
    return _HTML_TAG_RE.sub(" ", html).replace("&nbsp;", " ").strip()


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    dt = parsedate_to_datetime(value)
    return dt or datetime.now()


def _iter_parts_with_path(
    part: MIMEPart, path: tuple[int, ...]
) -> Iterator[tuple[MIMEPart, tuple[int, ...]]]:
    """按 RFC 3501 风格 MIME part 路径遍历叶子节点（多部件节点自身不产生附件）。"""
    if part.is_multipart():
        for i, sub in enumerate(part.iter_parts(), start=1):
            yield from _iter_parts_with_path(sub, path + (i,))
    else:
        yield part, path


def _attachments(part: MIMEPart) -> list[AttachmentMeta]:
    out: list[AttachmentMeta] = []
    for leaf, path in _iter_parts_with_path(part, ()):
        filename = leaf.get_filename()
        if filename and leaf.get_content_disposition() == "attachment":
            out.append(
                AttachmentMeta(
                    filename=_decode(filename),
                    size=len(leaf.get_content()),
                    mime_type=leaf.get_content_type(),
                    part_id=".".join(str(i) for i in path),
                )
            )
    return out


def find_part_by_path(part: MIMEPart, path: tuple[int, ...]) -> MIMEPart | None:
    """按 MIME part 路径定位部件；不存在返回 None。"""
    current = part
    for index in path:
        if not current.is_multipart():
            return None
        children = list(current.iter_parts())
        if index < 1 or index > len(children):
            return None
        current = children[index - 1]
    return current


def parse_email_message(raw: bytes, *, folder: str, uid: str) -> EmailMessage:
    """把 IMAP FETCH 的原始 RFC 822 字节解析为 EmailMessage。"""
    msg = email.message_from_bytes(raw, policy=policy.default)
    headers = {k: v for k, v in msg.items()}
    body = _first_text_plain(msg) or _strip_html(_first_text_html(msg))
    from_addrs = _addresses(msg.get("From"))
    return EmailMessage(
        id=f"{folder}:{uid}",
        account_id="default",
        folder=folder,
        subject=_decode(msg.get("Subject")),
        from_=from_addrs[0] if from_addrs else EmailAddress(email=""),
        to=_addresses(msg.get("To")),
        cc=_addresses(msg.get("Cc")),
        date=_parse_date(msg.get("Date")),
        body=body,
        body_html=_first_text_html(msg) or None,
        attachments=_attachments(msg),
        message_id=msg.get("Message-ID", ""),
        in_reply_to=msg.get("In-Reply-To"),
        headers=headers,
    )
