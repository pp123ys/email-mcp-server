from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class SchedulerStore:
    """JSON 文件持久化的调度队列（scheduled_sends / snoozes）。"""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {"scheduled_sends": [], "snoozes": []}
        with self.path.open("r", encoding="utf-8") as f:
            data: dict[str, list[dict[str, Any]]] = json.load(f)
            return data

    def _save(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_scheduled_send(self, item: dict[str, Any]) -> None:
        data = self.load()
        data["scheduled_sends"].append(item)
        self._save(data)

    def add_snooze(self, item: dict[str, Any]) -> None:
        data = self.load()
        data["snoozes"].append(item)
        self._save(data)

    def due_scheduled_sends(self, now: datetime) -> list[dict[str, Any]]:
        return [i for i in self.load()["scheduled_sends"] if _parse_dt(i["send_at"]) <= now]

    def due_snoozes(self, now: datetime) -> list[dict[str, Any]]:
        return [i for i in self.load()["snoozes"] if _parse_dt(i["until"]) <= now]

    def remove(self, kind: str, item_id: str) -> None:
        data = self.load()
        data[kind] = [i for i in data[kind] if i.get("id") != item_id]
        self._save(data)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class Scheduler:
    """到期执行器：发送到期的定时邮件、唤醒到期的 snooze。"""

    def __init__(
        self,
        store: SchedulerStore,
        send_fn: Callable[[dict[str, Any]], None],
        snooze_fn: Callable[[dict[str, Any]], None],
        interval_seconds: int = 30,
    ):
        self.store = store
        self.send_fn = send_fn
        self.snooze_fn = snooze_fn
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def process_due(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        for item in self.store.due_scheduled_sends(now):
            self.send_fn(item)
            self.store.remove("scheduled_sends", item["id"])
        for item in self.store.due_snoozes(now):
            self.snooze_fn(item)
            self.store.remove("snoozes", item["id"])

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self.process_due()
