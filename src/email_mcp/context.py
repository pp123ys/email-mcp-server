from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from email_mcp.config import send_rate_limit
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.email_service import EmailService
from email_mcp.service.guardrails import RateLimiter
from email_mcp.service.scheduler import Scheduler, SchedulerStore
from email_mcp.service.thread_service import ThreadService
from email_mcp.service.unsubscribe_service import UnsubscribeService


@dataclass
class AppContext:
    """服务器运行时的共享依赖容器。account 为 None 表示未配置（无凭据启动）。"""

    account: Account | None = None
    provider: EmailProvider | None = None
    configured: bool = field(default=False, init=False)
    email_service: EmailService | None = field(default=None, init=False)
    thread_service: ThreadService | None = field(default=None, init=False)
    unsubscribe_service: UnsubscribeService | None = field(default=None, init=False)
    scheduler: Scheduler | None = field(default=None, init=False)
    scheduler_store: SchedulerStore | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.configure()

    def configure(self, account: Account | None = None) -> None:
        """用账号配置（重）建服务；account 为 None 时用 self.account。配置失败则保持未配置状态。"""
        if account is not None:
            self.account = account
        if self.account is None or self.provider is None:
            self.configured = False
            return
        # 用局部非 None 引用：字段是 Optional，mypy strict 下无法在回调中收窄
        scheduler_store = SchedulerStore(Path("data/scheduler.json"))
        self.scheduler_store = scheduler_store
        email_service = EmailService(
            self.provider, self.account, scheduler_store, RateLimiter(send_rate_limit())
        )
        self.email_service = email_service
        self.thread_service = ThreadService(self.provider, self.account)
        self.unsubscribe_service = UnsubscribeService(self.provider, self.account)

        def send(item: dict[str, Any]) -> None:
            result = email_service.send_email(
                to=item["to"], subject=item["subject"], body=item["body"]
            )
            # send_email 把错误包成 {success: False} dict 而非抛异常；
            # 不在此抛异常的话 Scheduler.process_due 会把失败项误删
            if not result["success"]:
                raise RuntimeError(result["error"]["message"])

        def snooze(item: dict[str, Any]) -> None:
            # snooze 到期时把邮件重新标记为未读，提醒用户处理
            result = email_service.mark_unread(item["email_id"])
            if not result["success"]:
                raise RuntimeError(result["error"]["message"])

        self.scheduler = Scheduler(
            scheduler_store,
            send_fn=send,
            snooze_fn=snooze,
        )
        self.configured = True

    def reload(self, account: Account) -> None:
        """配置工具热重载：用新账号重建服务。"""
        self.configure(account)
