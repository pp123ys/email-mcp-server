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
