from datetime import datetime, timedelta, timezone

from email_mcp.service.scheduler import SchedulerStore


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
