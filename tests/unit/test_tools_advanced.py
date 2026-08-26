import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_unsubscribe_tool(account, provider):
    provider.messages[0].headers = {"List-Unsubscribe": "<mailto:unsub@news.com>"}
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("unsubscribe", {"email_id": "INBOX:1"})
    assert "unsub@news.com" in str(result)
    assert provider.sent[0]["to"] == ["unsub@news.com"]


@pytest.mark.asyncio
async def test_batch_send_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool(
        "batch_send", {"to": ["a@b.com", "c@d.com"], "subject": "Hi", "body": "Hello"}
    )
    assert "sent" in str(result)
    assert len(provider.sent) == 2


@pytest.mark.asyncio
async def test_schedule_send_tool(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore

    ctx = AppContext(account=account, provider=provider)
    store = SchedulerStore(tmp_path / "sched.json")
    ctx.scheduler_store = store
    ctx.scheduler.store = store
    # schedule_send 走 EmailService 持有的 store，必须一并换到 tmp_path
    assert ctx.email_service is not None
    ctx.email_service.scheduler_store = store
    mcp = build_server(ctx)
    result = await mcp.call_tool(
        "schedule_send",
        {
            "to": ["a@b.com"],
            "subject": "Later",
            "body": "Hi",
            "send_at": "2099-01-01T09:00:00+00:00",
        },
    )
    assert "schedule_id" in str(result)
    assert store.load()["scheduled_sends"][0]["subject"] == "Later"


@pytest.mark.asyncio
async def test_create_label_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("create_label", {"name": "Work"})
    assert "Work" in str(result)


@pytest.mark.asyncio
async def test_manage_labels_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("manage_labels", {"action": "list"})
    assert "INBOX" in str(result)
    result = await mcp.call_tool(
        "manage_labels", {"action": "delete", "name": "Missing"}
    )
    assert "deleted" in str(result)
