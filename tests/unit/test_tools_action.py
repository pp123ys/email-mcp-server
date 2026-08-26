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


@pytest.mark.asyncio
async def test_forward_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool(
        "forward_email", {"email_id": "INBOX:1", "to": ["f@b.com"], "body": "FYI"}
    )
    assert "success" in str(result)
    assert provider.sent[0]["to"] == ["f@b.com"]


@pytest.mark.asyncio
async def test_mark_unread_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("mark_unread", {"email_id": "INBOX:1"})
    assert "success" in str(result)


@pytest.mark.asyncio
async def test_archive_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("archive", {"email_id": "INBOX:1"})
    assert "success" in str(result)
    assert provider.get_message(account, "All Mail", "1").folder == "All Mail"


@pytest.mark.asyncio
async def test_trash_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("trash_email", {"email_id": "INBOX:1"})
    assert "success" in str(result)
    assert provider.get_message(account, "Trash", "1").folder == "Trash"


@pytest.mark.asyncio
async def test_set_flag_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("set_flag", {"email_id": "INBOX:1", "flag": "\\Flagged"})
    assert "success" in str(result)
    assert "\\Flagged" in provider.get_message(account, "INBOX", "1").flags


@pytest.mark.asyncio
async def test_pin_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("pin_email", {"email_id": "INBOX:1"})
    assert "success" in str(result)
    assert "\\Flagged" in provider.get_message(account, "INBOX", "1").flags


@pytest.mark.asyncio
async def test_snooze_tool(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore

    ctx = AppContext(account=account, provider=provider)
    store = SchedulerStore(tmp_path / "sched.json")
    ctx.scheduler_store = store
    ctx.scheduler.store = store
    assert ctx.email_service is not None
    ctx.email_service.scheduler_store = store
    mcp = build_server(ctx)
    result = await mcp.call_tool(
        "snooze_email", {"email_id": "INBOX:1", "until": "2099-01-01T09:00:00+00:00"}
    )
    assert "snoozed_until" in str(result)
    assert store.load()["snoozes"][0]["email_id"] == "INBOX:1"
