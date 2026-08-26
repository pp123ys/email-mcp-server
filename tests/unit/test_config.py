import os

import pytest

from email_mcp.config import http_token, load_account, save_account, send_rate_limit
from email_mcp.errors import EmailMCPError, ErrorCode


@pytest.fixture(autouse=True)
def _clean_email_env(monkeypatch):
    """清除 os.environ 中残留的 EMAIL_* 变量，避免跨测试污染。"""
    for key in list(os.environ):
        if key.startswith("EMAIL_"):
            monkeypatch.delenv(key, raising=False)


def test_load_account_from_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "EMAIL_IMAP_HOST=imap.x.com\nEMAIL_SMTP_HOST=smtp.x.com\n"
        "EMAIL_USERNAME=u@x.com\nEMAIL_AUTH_SECRET=secret\n",
        encoding="utf-8",
    )
    account = load_account(str(env))
    assert account.username == "u@x.com"
    assert account.auth_secret == "secret"
    assert account.imap_port == 993
    assert account.auth_mode == "app_password"


def test_missing_required_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EMAIL_IMAP_HOST=imap.x.com\n", encoding="utf-8")
    with pytest.raises(EmailMCPError) as ei:
        load_account(str(env))
    assert ei.value.code == ErrorCode.CONFIG_MISSING


def test_invalid_auth_mode_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "EMAIL_IMAP_HOST=imap\nEMAIL_SMTP_HOST=smtp\nEMAIL_USERNAME=u@x.com\n"
        "EMAIL_AUTH_SECRET=s\nEMAIL_AUTH_MODE=oops\n",
        encoding="utf-8",
    )
    with pytest.raises(EmailMCPError) as ei:
        load_account(str(env))
    assert ei.value.code == ErrorCode.CONFIG_INVALID


def test_invalid_port_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "EMAIL_IMAP_HOST=imap\nEMAIL_SMTP_HOST=smtp\nEMAIL_USERNAME=u@x.com\n"
        "EMAIL_AUTH_SECRET=s\nEMAIL_IMAP_PORT=abc\n",
        encoding="utf-8",
    )
    with pytest.raises(EmailMCPError) as ei:
        load_account(str(env))
    assert ei.value.code == ErrorCode.CONFIG_INVALID


def test_send_rate_limit_invalid_returns_default(monkeypatch):
    monkeypatch.setenv("EMAIL_SEND_RATE_LIMIT", "not-a-number")
    assert send_rate_limit() == 10


def test_http_token_empty_returns_none(monkeypatch):
    monkeypatch.setenv("EMAIL_HTTP_TOKEN", "")
    assert http_token() is None


def test_load_account_strict_false_returns_none_when_missing(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EMAIL_IMAP_HOST=imap.x.com\n", encoding="utf-8")
    assert load_account(str(env), strict=False) is None


def test_save_account_roundtrip(tmp_path):
    from email_mcp.models import Account

    env = tmp_path / ".env"
    account = Account(
        imap_host="imap.x.com", smtp_host="smtp.x.com", username="u@x.com",
        auth_secret="secret", auth_mode="password",
    )
    save_account(account, str(env))
    loaded = load_account(str(env), strict=True)
    assert loaded is not None
    assert loaded.username == "u@x.com"
    assert loaded.auth_secret == "secret"
    assert loaded.auth_mode == "password"
    assert loaded.imap_port == 993


def test_save_account_merges_existing(tmp_path):
    from email_mcp.models import Account

    env = tmp_path / ".env"
    env.write_text("EMAIL_IMAP_HOST=old.host\nSOME_OTHER_KEY=keepme\n", encoding="utf-8")
    account = Account(
        imap_host="new.host", smtp_host="smtp.x.com", username="u@x.com",
        auth_secret="s", sent_folder="[Gmail]/Sent Mail",
    )
    save_account(account, str(env))
    text = env.read_text(encoding="utf-8")
    assert "EMAIL_IMAP_HOST=new.host" in text
    assert "SOME_OTHER_KEY=keepme" in text
    assert "EMAIL_SENT_FOLDER=[Gmail]/Sent Mail" in text
