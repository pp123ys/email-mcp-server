from __future__ import annotations

import threading
import time

from email_mcp.errors import EmailMCPError, ErrorCode

BATCH_SIZE_LIMIT = 20


def check_batch_size(to: list[str]) -> None:
    """批量发送上限：每批 20 封。"""
    if len(to) > BATCH_SIZE_LIMIT:
        raise EmailMCPError(
            ErrorCode.BATCH_LIMIT_EXCEEDED,
            f"批量发送每批最多 {BATCH_SIZE_LIMIT} 封，收到 {len(to)} 封",
        )


class RateLimiter:
    """简单滑动窗口发送频率限制（每分钟 N 次）。"""

    def __init__(self, max_per_minute: int = 10):
        self.max_per_minute = max_per_minute
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def check(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._timestamps = [t for t in self._timestamps if now - t < 60]
            if len(self._timestamps) >= self.max_per_minute:
                raise EmailMCPError(
                    ErrorCode.RATE_LIMITED,
                    f"发送频率超限：每分钟最多 {self.max_per_minute} 封",
                )
            self._timestamps.append(now)
