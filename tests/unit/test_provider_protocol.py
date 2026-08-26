from typing import Protocol

from email_mcp.provider.base import EmailProvider


def test_provider_is_a_protocol():
    assert isinstance(EmailProvider, type)
    assert issubclass(EmailProvider, Protocol)


def test_protocol_has_required_methods():
    required = {
        "list_messages", "get_message", "get_thread", "search",
        "list_folders", "get_attachments", "download_attachment",
        "get_headers", "save_draft", "list_drafts", "send",
        "mark_read", "mark_unread", "move", "trash", "archive",
        "set_flag",
    }
    assert required.issubset(EmailProvider.__dict__.keys())
