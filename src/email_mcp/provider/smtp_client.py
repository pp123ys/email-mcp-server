from __future__ import annotations

import email.utils
import smtplib
import time
from email.message import EmailMessage

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account

DEFAULT_TIMEOUT = 15.0
RETRY_ATTEMPTS = 3  # 首次尝试 + 2 次重试
RETRY_DELAY_BASE = 0.5


def _safe_quit(server: smtplib.SMTP) -> None:
    try:
        server.quit()
    except Exception:
        pass


class SMTPClient:
    """SMTP 发送：TLS 连接、登录、发送、错误映射。"""

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

    def _connect(self) -> smtplib.SMTP:
        """建连（含重试）。TimeoutError → CONNECTION_TIMEOUT，其余 → SMTP_CONNECT_FAILED。"""
        last_exc: Exception | None = None
        for attempt in range(self.retry_attempts):
            try:
                if self.account.smtp_ssl:
                    return smtplib.SMTP_SSL(
                        self.account.smtp_host, self.account.smtp_port, timeout=self.timeout
                    )
                server = smtplib.SMTP(
                    self.account.smtp_host, self.account.smtp_port, timeout=self.timeout
                )
                server.starttls()
                return server
            except TimeoutError as exc:
                last_exc = exc
                time.sleep(self.retry_delay_base * (2**attempt))
            except (OSError, smtplib.SMTPException) as exc:
                last_exc = exc
                time.sleep(self.retry_delay_base * (2**attempt))
        if isinstance(last_exc, TimeoutError):
            raise EmailMCPError(
                ErrorCode.CONNECTION_TIMEOUT,
                f"连接 SMTP 服务器超时 {self.account.smtp_host}:{self.account.smtp_port}",
            ) from last_exc
        raise EmailMCPError(
            ErrorCode.SMTP_CONNECT_FAILED,
            f"无法连接 SMTP 服务器 {self.account.smtp_host}:{self.account.smtp_port}",
        ) from last_exc

    def send(
        self,
        *,
        to: list[str],
        cc: list[str] | None,
        subject: str,
        body: str,
        sender: str,
    ) -> str:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        message.set_content(body)
        message["Message-ID"] = email.utils.make_msgid(domain=self.account.smtp_host)

        server = self._connect()
        try:
            server.login(self.account.username, self.account.auth_secret)
            server.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailMCPError(
                ErrorCode.SMTP_AUTH_FAILED, "SMTP 认证失败，请检查账号密码或授权码"
            ) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise EmailMCPError(
                ErrorCode.INVALID_RECIPIENT,
                "SMTP 服务器拒绝了部分收件人",
                {"refused": {addr: str(resp) for addr, resp in exc.recipients.items()}},
            ) from exc
        except smtplib.SMTPException as exc:
            raise EmailMCPError(ErrorCode.INTERNAL, f"SMTP 发送失败: {exc}") from exc
        except OSError as exc:
            raise EmailMCPError(
                ErrorCode.SMTP_CONNECT_FAILED,
                f"SMTP 发送过程中连接中断 {self.account.smtp_host}:{self.account.smtp_port}",
            ) from exc
        finally:
            _safe_quit(server)

        return message["Message-ID"] or f"sent-{len(to)}@local"

    def check(self) -> None:
        """验证 SMTP 连接与登录（不发送邮件），供 test_email_connection 使用。"""
        server = self._connect()
        try:
            server.login(self.account.username, self.account.auth_secret)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailMCPError(
                ErrorCode.SMTP_AUTH_FAILED, "SMTP 认证失败，请检查账号密码或授权码"
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailMCPError(
                ErrorCode.SMTP_CONNECT_FAILED,
                f"SMTP 连接中断 {self.account.smtp_host}:{self.account.smtp_port}",
            ) from exc
        finally:
            _safe_quit(server)
