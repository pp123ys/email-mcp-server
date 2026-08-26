from email_mcp.service.email_service import EmailService
from email_mcp.service.quoting import build_quote_block


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_build_quote_block():
    block = build_quote_block("Sender Name", "2026-01-01 10:00", "original body")
    assert "Sender Name" in block
    assert "original body" in block
    assert "> original body" in block  # 引用行带 > 前缀
    assert block.startswith("On 2026-01-01 10:00 Sender Name wrote:")


def test_reply_email_prefills_and_quotes(account, provider):
    svc = make_service(account, provider)
    result = svc.reply_email("INBOX:1", body="Thanks!")
    assert result["success"] is True
    sent = provider.sent[0]
    assert sent["to"] == ["sender@x.com"]
    assert "Thanks!" in sent["body"]
    assert "> " in sent["body"]


def test_forward_email(account, provider):
    svc = make_service(account, provider)
    result = svc.forward_email("INBOX:1", to=["f@b.com"], body="FYI")
    assert result["success"] is True
    assert provider.sent[0]["to"] == ["f@b.com"]


def test_mark_read_unread(account, provider):
    svc = make_service(account, provider)
    svc.mark_read("INBOX:2")
    svc.mark_unread("INBOX:1")
    assert "\\Seen" in provider.get_message(account, "INBOX", "2").flags
    assert "\\Seen" not in provider.get_message(account, "INBOX", "1").flags


def test_archive_and_trash_are_soft(account, provider):
    svc = make_service(account, provider)
    svc.archive("INBOX:1")
    svc.trash_email("INBOX:2")
    assert provider.get_message(account, "All Mail", "1").folder == "All Mail"
    assert provider.get_message(account, "Trash", "2").folder == "Trash"


def test_move_email(account, provider):
    svc = make_service(account, provider)
    result = svc.move_email("INBOX:1", "Projects")
    assert result["success"] is True
    assert provider.get_message(account, "Projects", "1").folder == "Projects"


def test_set_flag_and_pin(account, provider):
    svc = make_service(account, provider)
    svc.pin_email("INBOX:1")
    assert "\\Flagged" in provider.get_message(account, "INBOX", "1").flags


def test_snooze_email_stores_item(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore

    store = SchedulerStore(tmp_path / "sched.json")
    svc = EmailService(provider=provider, account=account, scheduler_store=store)
    result = svc.snooze_email("INBOX:1", "2099-01-01T09:00:00+00:00")
    assert result["success"] is True
    assert store.load()["snoozes"][0]["email_id"] == "INBOX:1"


def test_reply_email_missing_message(account, provider):
    svc = make_service(account, provider)
    result = svc.reply_email("INBOX:999", body="Hi")
    assert result["success"] is False
    assert result["error"]["code"] == "EMAIL_NOT_FOUND"


def test_reply_email_invalid_cc(account, provider):
    svc = make_service(account, provider)
    result = svc.reply_email("INBOX:1", body="Hi", cc=["bad-cc"])
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_RECIPIENT"


def test_snooze_without_store(account, provider):
    svc = EmailService(provider=provider, account=account, scheduler_store=None)
    result = svc.snooze_email("INBOX:1", "2099-01-01T09:00:00+00:00")
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_MISSING"


def test_set_flag_rejects_invalid_flag(account, provider):
    svc = make_service(account, provider)
    result = svc.set_flag("INBOX:1", flag="bad)flag")
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"


def test_snooze_same_email_twice_removes_individually(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore

    store = SchedulerStore(tmp_path / "sched.json")
    svc = EmailService(provider=provider, account=account, scheduler_store=store)
    svc.snooze_email("INBOX:1", "2099-01-01T09:00:00+00:00")
    svc.snooze_email("INBOX:1", "2099-01-02T09:00:00+00:00")
    items = store.load()["snoozes"]
    assert len(items) == 2
    assert items[0]["id"] != items[1]["id"]  # 每条 snooze 独立 id，避免到期时误删全部
    store.remove("snoozes", items[0]["id"])
    remaining = store.load()["snoozes"]
    assert len(remaining) == 1
    assert remaining[0]["email_id"] == "INBOX:1"


def test_mark_read_is_idempotent(account, provider):
    svc = make_service(account, provider)
    svc.mark_read("INBOX:2")
    svc.mark_read("INBOX:2")
    flags = provider.get_message(account, "INBOX", "2").flags
    assert flags.count("\\Seen") == 1


def test_forward_email_missing_message(account, provider):
    svc = make_service(account, provider)
    result = svc.forward_email("INBOX:999", to=["f@b.com"], body="FYI")
    assert result["success"] is False
    assert result["error"]["code"] == "EMAIL_NOT_FOUND"
    assert provider.sent == []


def test_snooze_email_invalid_until(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore

    store = SchedulerStore(tmp_path / "sched.json")
    svc = EmailService(provider=provider, account=account, scheduler_store=store)
    result = svc.snooze_email("INBOX:1", "not-a-date")
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"
    assert store.load()["snoozes"] == []


def test_set_flag_rejects_illegal_char_in_keyword_flag(account, provider):
    # $ 开头关键字通过第一层校验，触发非法字符分支
    svc = make_service(account, provider)
    result = svc.set_flag("INBOX:1", flag="$custom)flag")
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"
