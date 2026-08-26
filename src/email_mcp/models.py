from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EmailAddress(BaseModel):
    """邮箱地址。"""

    name: str | None = None
    email: str


class AttachmentMeta(BaseModel):
    """附件元信息（内容不加载进内存）。"""

    filename: str
    size: int
    mime_type: str
    part_id: str  # 供 download_attachment 定位


class EmailMessage(BaseModel):
    """一封邮件的完整表示。"""

    id: str  # 格式 "folder:uid"
    account_id: str
    folder: str
    subject: str
    from_: EmailAddress
    to: list[EmailAddress] = Field(default_factory=list)
    cc: list[EmailAddress] = Field(default_factory=list)
    date: datetime
    flags: list[str] = Field(default_factory=list)  # 如 \\Seen \\Flagged
    body: str  # 纯文本正文（HTML 已剥离）
    body_html: str | None = None
    attachments: list[AttachmentMeta] = Field(default_factory=list)
    message_id: str = ""  # RFC 822 Message-ID，线程关联用
    in_reply_to: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class Account(BaseModel):
    """账号配置。v1 单实例，字段已多账号化。"""

    account_id: str = "default"
    imap_host: str = Field(min_length=1)
    imap_port: int = 993
    imap_ssl: bool = True
    smtp_host: str = Field(min_length=1)
    smtp_port: int = 465
    smtp_ssl: bool = True
    username: str
    auth_mode: Literal["app_password", "password"] = "app_password"
    auth_secret: str = ""  # 只从环境变量注入，绝不落日志
    sent_folder: str = "Sent"
