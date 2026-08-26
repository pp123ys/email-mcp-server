from __future__ import annotations

import imaplib
from contextlib import contextmanager
from typing import Iterator

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account

DEFAULT_TIMEOUT = 15.0


def _safe_logout(conn: imaplib.IMAP4) -> None:
    try:
        conn.logout()
    except Exception:
        pass


class IMAPClient:
    """IMAP 连接管理：SSL 连接、登录、超时、错误映射。"""

    def __init__(self, account: Account, timeout: float = DEFAULT_TIMEOUT):
        self.account = account
        self.timeout = timeout

    @contextmanager
    def connect(self) -> Iterator[imaplib.IMAP4]:
        conn: imaplib.IMAP4
        try:
            if self.account.imap_ssl:
                conn = imaplib.IMAP4_SSL(
                    self.account.imap_host, self.account.imap_port, timeout=self.timeout
                )
            else:
                conn = imaplib.IMAP4(
                    self.account.imap_host, self.account.imap_port, timeout=self.timeout
                )
        except (OSError, imaplib.IMAP4.error) as exc:
            raise EmailMCPError(
                ErrorCode.IMAP_CONNECT_FAILED,
                f"无法连接 IMAP 服务器 {self.account.imap_host}:{self.account.imap_port}",
            ) from exc
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
