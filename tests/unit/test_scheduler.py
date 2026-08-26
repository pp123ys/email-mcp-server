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


def test_store_load_corrupt_json_resets(tmp_path):
    store = make_store(tmp_path)
    store.path.write_text("{not-json", encoding="utf-8")
    assert store.load() == {"scheduled_sends": [], "snoozes": []}


def test_due_scheduled_sends_skips_malformed(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send({"id": "bad"})  # 缺 send_at
    store.add_scheduled_send({"id": "good", "send_at": "2000-01-01T00:00:00+00:00"})
    due = store.due_scheduled_sends(datetime.now(timezone.utc))
    assert [d["id"] for d in due] == ["good"]


def test_due_snoozes_skips_malformed(tmp_path):
    store = make_store(tmp_path)
    store.add_snooze({"id": "bad"})  # 缺 until
    store.add_snooze({"id": "good", "until": "2000-01-01T00:00:00+00:00"})
    due = store.due_snoozes(datetime.now(timezone.utc))
    assert [d["id"] for d in due] == ["good"]


def test_due_treats_naive_datetime_as_utc(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send({"id": "naive", "send_at": "2000-01-01T00:00:00"})
    due = store.due_scheduled_sends(datetime.now(timezone.utc))
    assert [d["id"] for d in due] == ["naive"]


def test_process_due_snooze_failure_keeps_item_and_continues(tmp_path):
    store = make_store(tmp_path)
    store.add_snooze({"id": "bad", "email_id": "INBOX:1", "until": "2000-01-01T00:00:00+00:00"})
    store.add_snooze({"id": "good", "email_id": "INBOX:2", "until": "2000-01-01T00:00:00+00:00"})
    woke: list[str] = []

    def flaky(item):
        if item["id"] == "bad":
            raise RuntimeError("wake boom")
        woke.append(item["id"])

    Scheduler(store, lambda item: None, flaky).process_due()
    assert woke == ["good"]
    assert [i["id"] for i in store.load()["snoozes"]] == ["bad"]


def test_scheduler_start_stop_roundtrip(tmp_path):
    store = make_store(tmp_path)
    scheduler = Scheduler(store, lambda item: None, lambda item: None, interval_seconds=1)
    scheduler.start()
    scheduler.start()  # 幂等：已启动时不新建线程
    scheduler.stop()
    assert scheduler._thread is None
    scheduler.start()  # stop 后可重启
    scheduler.stop()


def test_scheduler_loop_processes_due(tmp_path):
    import time

    store = make_store(tmp_path)
    store.add_scheduled_send(
        {"id": "a", "to": [], "subject": "", "body": "", "send_at": "2000-01-01T00:00:00+00:00"}
    )
    sent: list[str] = []
    scheduler = Scheduler(
        store, lambda item: sent.append(item["id"]), lambda item: None, interval_seconds=0.05
    )
    scheduler.start()
    try:
        deadline = time.monotonic() + 3
        while not sent and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        scheduler.stop()
    assert sent == ["a"]
    assert store.load()["scheduled_sends"] == []
