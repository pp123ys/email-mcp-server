from datetime import datetime, timedelta, timezone

from email_mcp.service.scheduler import Scheduler, SchedulerStore


def make_store(tmp_path):
    return SchedulerStore(tmp_path / "scheduler.json")


def test_store_persists_roundtrip(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send(
        {
            "id": "s1",
            "to": ["a@b.com"],
            "subject": "x",
            "body": "y",
            "send_at": "2026-09-01T09:00:00+00:00",
        }
    )
    store2 = make_store(tmp_path)
    assert store2.load()["scheduled_sends"][0]["id"] == "s1"


def test_due_scheduled_sends(tmp_path):
    store = make_store(tmp_path)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    store.add_scheduled_send({"id": "past", "to": [], "subject": "", "body": "", "send_at": past})
    store.add_scheduled_send(
        {"id": "future", "to": [], "subject": "", "body": "", "send_at": future}
    )
    now = datetime.now(timezone.utc)
    due = store.due_scheduled_sends(now)
    assert [d["id"] for d in due] == ["past"]


def test_remove(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send({"id": "a", "to": [], "subject": "", "body": "", "send_at": "x"})
    store.remove("scheduled_sends", "a")
    assert store.load()["scheduled_sends"] == []


def test_process_due_executes_and_removes(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send(
        {
            "id": "a",
            "to": [],
            "subject": "",
            "body": "",
            "send_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        }
    )
    store.add_snooze(
        {
            "id": "z",
            "email_id": "INBOX:1",
            "until": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        }
    )
    sent, snoozed = [], []
    scheduler = Scheduler(store, lambda item: sent.append(item), lambda item: snoozed.append(item))
    scheduler.process_due()
    assert [i["id"] for i in sent] == ["a"]
    assert [i["id"] for i in snoozed] == ["z"]
    assert store.load()["scheduled_sends"] == []
    assert store.load()["snoozes"] == []


def test_process_due_uses_aware_now(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send(
        {
            "id": "future",
            "to": [],
            "subject": "",
            "body": "",
            "send_at": "2099-09-01T09:00:00+00:00",
        }
    )
    sent = []
    Scheduler(store, lambda item: sent.append(item), lambda item: None).process_due()  # 默认 now
    assert sent == []


def test_process_due_failure_keeps_item_and_continues(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send(
        {"id": "bad", "to": [], "subject": "", "body": "", "send_at": "2000-01-01T00:00:00+00:00"}
    )
    store.add_scheduled_send(
        {"id": "good", "to": [], "subject": "", "body": "", "send_at": "2000-01-01T00:00:00+00:00"}
    )
    sent: list[str] = []

    def flaky(item):
        if item["id"] == "bad":
            raise RuntimeError("smtp boom")
        sent.append(item["id"])

    Scheduler(store, flaky, lambda item: None).process_due()
    assert sent == ["good"]
    assert [i["id"] for i in store.load()["scheduled_sends"]] == ["bad"]
