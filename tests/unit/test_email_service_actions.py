from email_mcp.service.email_service import EmailService, build_quote_block


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
