from __future__ import annotations

import email.utils
import smtplib
from email.message import EmailMessage

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account

DEFAULT_TIMEOUT = 15.0


def _safe_quit(server: smtplib.SMTP) -> None:
    try:
        server.quit()
    except Exception:
        pass


class SMTPClient:
    """SMTP 发送：TLS 连接、登录、发送、错误映射。"""

    def __init__(self, account: Account, timeout: float = DEFAULT_TIMEOUT):
        self.account = account
        self.timeout = timeout

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

        server: smtplib.SMTP
        try:
            if self.account.smtp_ssl:
                server = smtplib.SMTP_SSL(
                    self.account.smtp_host, self.account.smtp_port, timeout=self.timeout
                )
            else:
                server = smtplib.SMTP(
                    self.account.smtp_host, self.account.smtp_port, timeout=self.timeout
                )
                server.starttls()
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailMCPError(
                ErrorCode.SMTP_CONNECT_FAILED,
                f"无法连接 SMTP 服务器 {self.account.smtp_host}:{self.account.smtp_port}",
            ) from exc

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
