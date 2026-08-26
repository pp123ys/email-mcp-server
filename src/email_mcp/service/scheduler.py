# src/email_mcp/service/scheduler.py
"""本地调度队列：定时发送与 snooze 的持久化与到期执行。

SchedulerStore 负责 JSON 文件持久化（线程安全：锁 + 原子写）；
Scheduler 负责到期执行（每项 try/except 隔离，单项失败不影响其余，
失败项保留待下次重试）。
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SchedulerStore:
    """JSON 文件持久化的调度队列（scheduled_sends / snoozes）。线程安全。"""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def load(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return self._load_unlocked()

    def _load_unlocked(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {"scheduled_sends": [], "snoozes": []}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data: dict[str, list[dict[str, Any]]] = json.load(f)
                return data
        except json.JSONDecodeError:
            logger.warning("调度队列文件损坏，重置为空队列: %s", self.path)
            return {"scheduled_sends": [], "snoozes": []}

    def _save(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)  # 原子替换，防崩溃写坏文件

    def _mutate(self, fn: Callable[[dict[str, list[dict[str, Any]]]], None]) -> None:
        with self._lock:
            data = self._load_unlocked()
            fn(data)
            self._save(data)

    def add_scheduled_send(self, item: dict[str, Any]) -> None:
        self._mutate(lambda d: d["scheduled_sends"].append(item))

    def add_snooze(self, item: dict[str, Any]) -> None:
        self._mutate(lambda d: d["snoozes"].append(item))

    def due_scheduled_sends(self, now: datetime) -> list[dict[str, Any]]:
        with self._lock:
            due: list[dict[str, Any]] = []
            for item in self._load_unlocked()["scheduled_sends"]:
                try:
                    if _parse_dt(item["send_at"]) <= now:
                        due.append(item)
                except (KeyError, ValueError, TypeError):
                    logger.warning("跳过格式异常的定时发送项: %s", item.get("id"))
            return due

    def due_snoozes(self, now: datetime) -> list[dict[str, Any]]:
        with self._lock:
            due: list[dict[str, Any]] = []
            for item in self._load_unlocked()["snoozes"]:
                try:
                    if _parse_dt(item["until"]) <= now:
                        due.append(item)
                except (KeyError, ValueError, TypeError):
                    logger.warning("跳过格式异常的 snooze 项: %s", item.get("id"))
            return due

    def remove(self, kind: str, item_id: str) -> None:
        def _remove(data: dict[str, list[dict[str, Any]]]) -> None:
            data[kind] = [i for i in data[kind] if i.get("id") != item_id]

        self._mutate(_remove)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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
        """执行所有到期项。单项失败仅记录日志并保留该项（下次重试），不影响其余项。"""
        now = now or datetime.now(timezone.utc)
        for item in self.store.due_scheduled_sends(now):
            try:
                self.send_fn(item)
            except Exception:
                logger.exception("定时发送失败，保留该项待重试: %s", item.get("id"))
                continue
            self.store.remove("scheduled_sends", item["id"])
        for item in self.store.due_snoozes(now):
            try:
                self.snooze_fn(item)
            except Exception:
                logger.exception("snooze 唤醒失败，保留该项待重试: %s", item.get("id"))
                continue
            self.store.remove("snoozes", item["id"])

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()  # 允许 stop() 后再次 start()
        logger.info("调度器后台循环启动（间隔 %ss）", self.interval)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止后台循环并等待线程退出（用于测试与优雅关闭）。"""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval + 5)
            self._thread = None
        logger.info("调度器已停止")

    def _loop(self) -> None:
        try:
            while not self._stop.wait(self.interval):
                self.process_due()
        finally:
            self._thread = None  # 允许 start() 重启
