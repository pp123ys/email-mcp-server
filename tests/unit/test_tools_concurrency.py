"""并发回归测试：慢工具不得阻塞事件循环（asyncio.to_thread 修复）。

修复前（同步工具在 asyncio 事件循环线程中直接执行）：slow 工具 sleep 1s
会阻塞整个事件循环，fast 请求无法在 0.5s 内完成 → 本测试失败。
修复后（async_run 经 asyncio.to_thread 在线程池执行）：fast 立即完成 → 通过。
"""
from __future__ import annotations

import asyncio
import time

import pytest

from email_mcp.context import AppContext
from email_mcp.server import build_server


@pytest.mark.asyncio
async def test_slow_tool_does_not_block_fast_request(account, provider, monkeypatch):
    def slow_list(
        self, account, folder, *, page, page_size, unread_only=False, from_email=None
    ):
        time.sleep(1.0)  # 模拟慢 IMAP 操作
        return ([], 0)

    monkeypatch.setattr(type(provider), "list_messages", slow_list)
    mcp = build_server(AppContext(account=account, provider=provider))

    # 先创建 slow 任务：若同步工具阻塞事件循环，slow 会占满循环 1s，
    # 此时 fast 无法执行，须等 slow 完成才运行 → 实测耗时 ≈1s（>0.5s）。
    # 修复后 slow 经 to_thread 在线程池执行，事件循环空闲，fast 立即完成（≈0s）。
    slow = asyncio.create_task(
        mcp.call_tool("list_inbox", {"page": 1, "page_size": 2})
    )
    fast = asyncio.create_task(mcp.call_tool("get_account_status", {}))
    t0 = time.monotonic()
    fast_result = await fast
    fast_elapsed = time.monotonic() - t0
    slow_result = await slow
    assert fast_elapsed < 0.5, (
        f"fast 工具被 slow 工具阻塞 {fast_elapsed:.3f}s（同步工具阻塞了事件循环）"
    )
    assert "configured" in str(fast_result)
    assert "success" in str(slow_result)


@pytest.mark.asyncio
async def test_async_run_wraps_sync(provider):
    from email_mcp.tools._guard import async_run

    calls = []

    @async_run
    def sync_fn(x: int) -> int:
        calls.append(x)
        return x * 2

    assert asyncio.iscoroutinefunction(sync_fn) is True
    result = await sync_fn(21)
    assert result == 42
    assert calls == [21]
