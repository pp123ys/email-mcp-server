from email_mcp.service.email_service import EmailService
from email_mcp.service.guardrails import BATCH_SIZE_LIMIT, RateLimiter


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_batch_send_ok(account, provider):
    svc = make_service(account, provider)
    result = svc.batch_send(to=["a@b.com", "c@d.com"], subject="Hi", body="Hello")
    assert result["success"] is True
    assert result["data"]["sent"] == 2
    assert len(provider.sent) == 2


def test_batch_send_over_limit(account, provider):
    svc = make_service(account, provider)
    result = svc.batch_send(
        to=[f"u{i}@x.com" for i in range(BATCH_SIZE_LIMIT + 1)],
        subject="Hi", body="Hello",
    )
    assert result["success"] is False
    assert result["error"]["code"] == "BATCH_LIMIT_EXCEEDED"
    assert provider.sent == []


def test_batch_send_rate_limited(account, provider):
    svc = EmailService(
        provider=provider,
        account=account,
        rate_limiter=RateLimiter(max_per_minute=1),
    )
    result = svc.batch_send(to=["a@b.com", "c@d.com"], subject="Hi", body="Hello")
    assert result["success"] is False
    assert result["error"]["code"] == "RATE_LIMITED"
    assert len(provider.sent) == 1


def test_schedule_send_stores_item(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore

    store = SchedulerStore(tmp_path / "sched.json")
    svc = EmailService(provider=provider, account=account, scheduler_store=store)
    result = svc.schedule_send(
        to=["a@b.com"], subject="Later", body="Hi",
        send_at="2099-01-01T09:00:00+00:00",
    )
    assert result["success"] is True
    assert store.load()["scheduled_sends"][0]["subject"] == "Later"


def test_create_label_creates_folder(account, provider):
    svc = make_service(account, provider)
    assert svc.create_label("Work")["success"] is True
    assert "Work" in provider.list_folders(account)


def test_manage_labels_list_and_delete(account, provider):
    svc = make_service(account, provider)
    svc.create_label("Work")
    data = svc.manage_labels(action="list")["data"]
    assert "Work" in data["labels"]
    assert svc.manage_labels(action="delete", name="Work")["success"] is True
    assert "Work" not in provider.list_folders(account)


def test_manage_labels_invalid_action(account, provider):
    svc = make_service(account, provider)
    result = svc.manage_labels(action="bogus")
    assert result["success"] is False
    assert result["error"]["code"] == "CONFIG_INVALID"
