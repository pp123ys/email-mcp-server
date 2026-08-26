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


def test_appcontext_scheduler_retains_failed_scheduled_send(
    account, provider, tmp_path, monkeypatch
):
    from email_mcp.errors import EmailMCPError, ErrorCode
    from email_mcp.service.scheduler import SchedulerStore

    ctx = AppContext(account=account, provider=provider)
    store = SchedulerStore(tmp_path / "sched.json")
    ctx.scheduler_store = store
    ctx.scheduler.store = store

    def boom(self, account, *, to, cc=None, subject, body):
        raise EmailMCPError(ErrorCode.SMTP_AUTH_FAILED, "auth failed")

    monkeypatch.setattr(type(provider), "send", boom)
    store.add_scheduled_send(
        {"id": "s1", "to": ["a@b.com"], "subject": "x", "body": "y",
         "send_at": "2000-01-01T00:00:00+00:00"}
    )
    ctx.scheduler.process_due()
    remaining = [i["id"] for i in store.load()["scheduled_sends"]]
    assert remaining == ["s1"]  # 失败项保留待重试（修复前会被静默删除）
