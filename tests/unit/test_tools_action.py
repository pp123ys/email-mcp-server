import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_reply_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("reply_email", {"email_id": "INBOX:1", "body": "Thanks!"})
    assert "success" in str(result)
    assert provider.sent[0]["to"] == ["sender@x.com"]


@pytest.mark.asyncio
async def test_mark_read_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("mark_read", {"email_id": "INBOX:2"})
    assert "success" in str(result)


@pytest.mark.asyncio
async def test_move_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("move_email", {"email_id": "INBOX:1", "dest_folder": "Projects"})
    assert "success" in str(result)
