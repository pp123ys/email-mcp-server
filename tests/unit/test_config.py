import os

import pytest

from email_mcp.config import load_account
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
