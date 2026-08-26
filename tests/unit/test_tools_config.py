import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_get_account_status_unconfigured(provider):
    ctx = AppContext(account=None, provider=provider)
    mcp = build_server(ctx)
    result = await mcp.call_tool("get_account_status", {})
    assert "configured" in str(result)
    assert "false" in str(result)


@pytest.mark.asyncio
async def test_get_account_status_configured(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = await mcp.call_tool("get_account_status", {})
    assert "me@test.local" in str(result)
    assert "s3cret" not in str(result)


@pytest.mark.asyncio
async def test_unconfigured_mail_tool_returns_config_missing(provider):
    ctx = AppContext(account=None, provider=provider)
    mcp = build_server(ctx)
    result = await mcp.call_tool("list_inbox", {})
    assert "CONFIG_MISSING" in str(result)


@pytest.mark.asyncio
async def test_configure_account_flow(provider, tmp_path):
    # 用一个可写的临时 .env 路径——ConfigService 默认写 cwd/.env，为避免污染仓库，
    # 这里直接测服务层（ConfigService(ctx, env_path=...)）。
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path=str(tmp_path / ".env"))
    result = service.configure_account(
        imap_host="imap.x.com", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="topsecret",
    )
    assert result["success"] is True
    assert ctx.configured is True
    assert ctx.account is not None and ctx.account.username == "u@x.com"
    # 密钥不泄露
    assert "topsecret" not in str(result)
    # 工具层读配置状态
    mcp = build_server(ctx)
    status = await mcp.call_tool("get_account_status", {})
    assert "u@x.com" in str(status)
    if ctx.scheduler is not None:
        ctx.scheduler.stop()  # 停掉 configure_account 启动的后台线程


def test_configure_account_strips_values(provider, tmp_path):
    # 校验用 strip() 但存储用原始值会导致 " u@x.com " 通过校验却原样存储，
    # 之后 test_email_connection 出现迷惑性认证失败——存储前必须 strip。
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path=str(tmp_path / ".env"))
    result = service.configure_account(
        imap_host="  imap.x.com  ", smtp_host=" smtp.x.com ",
        username=" u@x.com ", auth_secret=" topsecret ",
    )
    assert result["success"] is True
    assert ctx.account is not None
    assert ctx.account.username == "u@x.com"
    assert ctx.account.imap_host == "imap.x.com"
    assert ctx.account.auth_secret == "topsecret"
    ctx.scheduler.stop()  # 清理后台线程


@pytest.mark.asyncio
async def test_configure_account_empty_secret(provider):
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path="unused")
    result = service.configure_account(
        imap_host="imap.x.com", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="",
    )
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"


def test_test_email_connection_unconfigured(provider):
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    result = ConfigService(ctx).test_email_connection()
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_MISSING"


@pytest.mark.asyncio
async def test_configure_account_starts_scheduler(provider, tmp_path):
    from email_mcp.service.config_service import ConfigService
    from email_mcp.service.scheduler import SchedulerStore

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path=str(tmp_path / ".env"))
    service.configure_account(
        imap_host="imap.x.com", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="topsecret",
    )
    assert ctx.scheduler is not None
    # 调度器可处理到期项（不依赖真实线程，直接 process_due 验证对象可用）；
    # 用 tmp store 避免污染仓库 data/scheduler.json
    store = SchedulerStore(tmp_path / "sched.json")
    ctx.scheduler_store = store
    ctx.scheduler.store = store
    store.add_scheduled_send(
        {"id": "s1", "to": ["a@b.com"], "subject": "x", "body": "y",
         "send_at": "2000-01-01T00:00:00+00:00"}
    )
    ctx.scheduler.process_due()
    assert [i["id"] for i in store.load()["scheduled_sends"]] == []
    assert len(provider.sent) == 1
    ctx.scheduler.stop()  # 停掉 configure_account 启动的后台线程


def test_configure_account_invalid_host(provider):
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path="unused")
    result = service.configure_account(
        imap_host="", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="topsecret",
    )
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"


def test_configure_account_blank_secret(provider):
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path="unused")
    result = service.configure_account(
        imap_host="imap.x.com", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="   ",
    )
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"


def test_configure_account_calls_start_scheduler(provider, tmp_path):
    # 修复前：configure_account 重建 Scheduler 但从不 start()，定时任务静默失效
    from unittest.mock import patch

    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path=str(tmp_path / ".env"))
    with patch("email_mcp.service.scheduler.Scheduler.start") as start_mock:
        result = service.configure_account(
            imap_host="imap.x.com", smtp_host="smtp.x.com",
            username="u@x.com", auth_secret="topsecret",
        )
    assert result["success"] is True
    start_mock.assert_called_once()


def test_reconfigure_stops_old_scheduler_and_starts_new(provider, tmp_path):
    # 已配置再配置：旧 Scheduler 必须 stop（防旧凭据闭包线程继续跑），新 Scheduler start
    from unittest.mock import patch

    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    service = ConfigService(ctx, env_path=str(tmp_path / ".env"))
    service.configure_account(
        imap_host="imap.x.com", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="topsecret",
    )
    old = ctx.scheduler
    assert old is not None
    with patch("email_mcp.service.scheduler.Scheduler.stop") as stop_mock, patch(
        "email_mcp.service.scheduler.Scheduler.start"
    ) as start_mock:
        result = service.configure_account(
            imap_host="imap2.x.com", smtp_host="smtp2.x.com",
            username="u@x.com", auth_secret="newsecret",
        )
    assert result["success"] is True
    stop_mock.assert_called_once()
    start_mock.assert_called_once()
    assert ctx.scheduler is not old
    old.stop()  # 清理第一个 configure_account 启动的真实线程（stop 被 mock，须显式停）


@pytest.mark.asyncio
async def test_mail_tool_works_after_configure_hot_reload(provider, tmp_path):
    # 服务启动未配置 → build_server 后经 configure_account 热重载，邮箱工具立即可用
    from email_mcp.service.config_service import ConfigService

    ctx = AppContext(account=None, provider=provider)
    mcp = build_server(ctx)
    result = await mcp.call_tool("list_inbox", {})
    assert "CONFIG_MISSING" in str(result)

    service = ConfigService(ctx, env_path=str(tmp_path / ".env"))
    configured = service.configure_account(
        imap_host="imap.x.com", smtp_host="smtp.x.com",
        username="u@x.com", auth_secret="topsecret",
    )
    assert configured["success"] is True

    result = await mcp.call_tool("list_inbox", {"page": 1, "page_size": 5})
    assert "CONFIG_MISSING" not in str(result)
    assert "s1" in str(result)
    if ctx.scheduler is not None:
        ctx.scheduler.stop()  # 停掉 configure_account 启动的后台线程
