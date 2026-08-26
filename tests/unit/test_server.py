import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_build_server_registers_tools(account, provider):
    ctx = AppContext(account=account, provider=provider)
    mcp = build_server(ctx)
    # mcp 1.29.1：FastMCP.list_tools 是 async 公开 API，需 await
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert {"list_inbox", "read_email", "send_email", "save_draft"} <= names
    assert len(names) == 27
