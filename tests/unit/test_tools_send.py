import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_send_email_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool(
        "send_email", {"to": ["a@b.com"], "subject": "Hi", "body": "Hello"}
    )
    assert "sent-" in str(result)


@pytest.mark.asyncio
async def test_send_email_invalid_recipient(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("send_email", {"to": ["bad"], "subject": "Hi", "body": "Hello"})
    assert "INVALID_RECIPIENT" in str(result)


@pytest.mark.asyncio
async def test_save_draft_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("save_draft", {"to": ["a@b.com"], "subject": "D", "body": "WIP"})
    assert "Drafts:" in str(result)


@pytest.mark.asyncio
async def test_list_drafts_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    await mcp.call_tool("save_draft", {"to": ["a@b.com"], "subject": "D", "body": "WIP"})
    result = await mcp.call_tool("list_drafts", {})
    assert "D" in str(result)
