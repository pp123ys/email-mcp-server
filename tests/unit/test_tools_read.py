import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_list_inbox_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("list_inbox", {"page": 1, "page_size": 2})
    assert "s1" in str(result)


@pytest.mark.asyncio
async def test_read_email_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("read_email", {"email_id": "INBOX:1"})
    assert "s1" in str(result)


@pytest.mark.asyncio
async def test_read_email_missing_returns_structured_error(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("read_email", {"email_id": "INBOX:999"})
    assert "EMAIL_NOT_FOUND" in str(result)


@pytest.mark.asyncio
async def test_search_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("search_emails", {"query": "s2"})
    assert "s2" in str(result)


@pytest.mark.asyncio
async def test_get_account_info_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("get_account_info", {})
    assert "me@test.local" in str(result)
    assert "s3cret" not in str(result)
