from __future__ import annotations

import imaplib
import time
from contextlib import contextmanager
from typing import Iterator

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account

DEFAULT_TIMEOUT = 15.0
RETRY_ATTEMPTS = 3  # 首次尝试 + 2 次重试
RETRY_DELAY_BASE = 0.5


def _safe_logout(conn: imaplib.IMAP4) -> None:
    try:
        conn.logout()
    except Exception:
        pass


class IMAPClient:
    """IMAP 连接管理：SSL 连接、登录、超时、错误映射。"""

    def __init__(
        self,
        account: Account,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = RETRY_ATTEMPTS,
        retry_delay_base: float = RETRY_DELAY_BASE,
    ):
        self.account = account
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay_base = retry_delay_base

    def _connect(self) -> imaplib.IMAP4:
        """建连（含重试）。TimeoutError → CONNECTION_TIMEOUT，其余 → IMAP_CONNECT_FAILED。"""
        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts):
            try:
                if self.account.imap_ssl:
                    return imaplib.IMAP4_SSL(
                        self.account.imap_host, self.account.imap_port, timeout=self.timeout
                    )
                return imaplib.IMAP4(
                    self.account.imap_host, self.account.imap_port, timeout=self.timeout
                )
            except TimeoutError as exc:
                last_exc = exc
                time.sleep(self.retry_delay_base * (2**attempt))
            except (OSError, imaplib.IMAP4.error) as exc:
                last_exc = exc
                time.sleep(self.retry_delay_base * (2**attempt))
        if isinstance(last_exc, TimeoutError):
            raise EmailMCPError(
                ErrorCode.CONNECTION_TIMEOUT,
                f"连接 IMAP 服务器超时 {self.account.imap_host}:{self.account.imap_port}",
            ) from last_exc
        raise EmailMCPError(
            ErrorCode.IMAP_CONNECT_FAILED,
            f"无法连接 IMAP 服务器 {self.account.imap_host}:{self.account.imap_port}",
        ) from last_exc

    @contextmanager
    def connect(self) -> Iterator[imaplib.IMAP4]:
        conn = self._connect()
        try:
            conn.login(self.account.username, self.account.auth_secret)
        except imaplib.IMAP4.error as exc:
            _safe_logout(conn)
            raise EmailMCPError(
                ErrorCode.IMAP_AUTH_FAILED, "IMAP 认证失败，请检查账号密码或授权码"
            ) from exc
        except OSError as exc:
            _safe_logout(conn)
            raise EmailMCPError(
                ErrorCode.IMAP_CONNECT_FAILED,
                f"IMAP 登录过程中连接中断 {self.account.imap_host}:{self.account.imap_port}",
            ) from exc
        try:
            yield conn
        finally:
            _safe_logout(conn)
