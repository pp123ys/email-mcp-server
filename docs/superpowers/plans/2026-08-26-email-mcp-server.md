# 邮件 MCP 服务器实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Python 邮件 MCP 服务器，通过 27 个 MCP 工具为外部 agent 提供完整的邮件读取/搜索/发送/操作能力（IMAP/SMTP 第一版，预留 Gmail/Outlook 适配层）。

**Architecture:** 五层单向依赖架构：传输层（FastMCP，stdio/Streamable HTTP 双入口）→ MCP Server（工具注册与参数校验）→ 服务层（EmailService/ThreadService/UnsubscribeService/Scheduler，纯业务逻辑）→ Provider 抽象层（EmailProvider Protocol + ImapProvider）→ 配置层（.env → Account）。任何一层都不反向依赖上层，均可独立测试替换。

**Tech Stack:** Python ≥3.11、官方 `mcp` SDK（FastMCP）、`pydantic` v2、`imaplib`/`smtplib`、`python-dotenv`、`email-validator`、`python-dateutil`；测试 `pytest`/`pytest-asyncio`，质量 `ruff`/`mypy`；依赖管理 `uv`。

**规格文档：** `docs/superpowers/specs/2026-08-26-email-mcp-server-design.md`

**全局约定（所有任务遵守）：**
- 每个任务按 TDD 循环：先写测试 → 运行确认失败 → 最小实现 → 运行确认通过 → 提交
- 提交信息用 `feat:` / `test:` / `docs:` 前缀
- 凭据（`auth_secret`）绝不写入日志、错误信息或测试断言
- 邮件 ID 格式为 `folder:uid`（按最后一个冒号切分）；文件夹名含冒号视为已知限制

---

## Phase 0：项目脚手架

### Task 1: uv 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/email_mcp/__init__.py`

- [ ] **Step 1: 初始化 uv 项目并添加依赖**

运行（在项目根目录 `D:\text\email service`）：

```bash
uv init --name email-mcp-server --package --python ">=3.11"
uv add mcp "pydantic>=2" python-dotenv email-validator python-dateutil
uv add --dev pytest pytest-asyncio ruff mypy
```

- [ ] **Step 2: 用完整内容替换 `pyproject.toml`**

```toml
[project]
name = "email-mcp-server"
version = "0.1.0"
description = "邮件 MCP 服务器：为外部 agent 提供 IMAP/SMTP 邮件工具"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "email-validator>=2.0",
    "python-dateutil>=2.9",
]

[project.scripts]
email-mcp = "email_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/email_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.mypy]
python_version = "3.11"
strict = true
```

- [ ] **Step 3: 创建 `.gitignore`**

```gitignore
.env
__pycache__/
*.pyc
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

- [ ] **Step 4: 创建 `.env.example`**

```bash
# 邮件账号配置（复制为 .env 并填写真实值，.env 已被 gitignore）
EMAIL_ACCOUNT_ID=default
EMAIL_IMAP_HOST=imap.example.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_SSL=true
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_SSL=true
EMAIL_USERNAME=you@example.com
# auth_mode: app_password（应用专用密码/授权码）或 password（主密码）
EMAIL_AUTH_MODE=app_password
EMAIL_AUTH_SECRET=your-app-password-or-main-password
EMAIL_SENT_FOLDER=Sent
# HTTP 模式 Bearer token（可选；不配置则只监听 localhost）
EMAIL_HTTP_TOKEN=
# 发送频率上限（每分钟，默认 10）
EMAIL_SEND_RATE_LIMIT=10
```

- [ ] **Step 5: 创建 `README.md`**

```markdown
# email-mcp-server

邮件 MCP 服务器：通过 MCP 协议为外部 agent（Claude Desktop / Cursor / 自研 agent）提供邮件工具。

## 能力
- 读取：收件箱列表、读邮件、线程、搜索、文件夹、附件、邮件头
- 发送：直接发送、存草稿（人工确认后手动发送）、定时发送、批量发送
- 操作：回复/转发、已读/未读、归档、移动、废纸篓、星标、延后、退订、标签

## 快速开始
1. `cp .env.example .env` 并填写 IMAP/SMTP 配置
2. `uv run email-mcp`（stdio 模式）或 `uv run email-mcp --http`（Streamable HTTP）
3. 在 Claude Desktop / Cursor 中把该命令配置为 MCP server

## 安全
- 凭据只从环境变量读取，日志/错误信息全部脱敏
- 批量发送限 20 封/批，发送频率可配置
- 删除一律软删（移入废纸篓）

## 测试
`uv run pytest` / `uv run ruff check .` / `uv run mypy src`
```

- [ ] **Step 6: 创建 `src/email_mcp/__init__.py`**

```python
"""email-mcp-server：邮件 MCP 服务器。"""

__version__ = "0.1.0"
```

- [ ] **Step 7: 验证脚手架可运行**

运行：`uv run python -c "import mcp, pydantic; print('ok')"`
期望：输出 `ok`，无错误。

- [ ] **Step 8: 提交**

```bash
git add pyproject.toml .gitignore .env.example README.md src/email_mcp/__init__.py
git commit -m "chore: 初始化 uv 项目与依赖"
```

---

## Phase 1：领域模型与错误框架

### Task 2: 领域模型 models.py

**Files:**
- Create: `src/email_mcp/models.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_models.py
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from email_mcp.models import Account, AttachmentMeta, EmailAddress, EmailMessage


def test_email_address_requires_email():
    addr = EmailAddress(email="a@b.com")
    assert addr.email == "a@b.com"
    assert addr.name is None


def test_email_message_defaults():
    msg = EmailMessage(
        id="INBOX:42",
        account_id="default",
        folder="INBOX",
        subject="Hi",
        from_=EmailAddress(email="x@y.com"),
        to=[EmailAddress(email="me@y.com")],
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        body="hello",
    )
    assert msg.cc == []
    assert msg.flags == []
    assert msg.attachments == []
    assert msg.body_html is None
    assert msg.message_id == ""


def test_attachment_meta_fields():
    a = AttachmentMeta(filename="a.pdf", size=10, mime_type="application/pdf", part_id="1")
    assert a.part_id == "1"


def test_account_requires_hosts():
    with pytest.raises(ValidationError):
        Account(imap_host="", smtp_host="", username="u@x.com")


def test_account_auth_mode_enum():
    with pytest.raises(ValidationError):
        Account(
            imap_host="imap", smtp_host="smtp", username="u@x.com",
            auth_mode="unknown",
        )
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_models.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.models'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/models.py
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
    imap_host: str
    imap_port: int = 993
    imap_ssl: bool = True
    smtp_host: str
    smtp_port: int = 465
    smtp_ssl: bool = True
    username: str
    auth_mode: Literal["app_password", "password"] = "app_password"
    auth_secret: str = ""  # 只从环境变量注入，绝不落日志
    sent_folder: str = "Sent"
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_models.py -v`
期望：PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/models.py tests/unit/test_models.py
git commit -m "feat: 领域模型 EmailMessage/Account/AttachmentMeta"
```

---

### Task 3: 错误框架 errors.py

**Files:**
- Create: `src/email_mcp/errors.py`
- Test: `tests/unit/test_errors.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_errors.py
import pytest
from email_mcp.errors import EmailMCPError, ErrorCode, error_result


def test_error_code_values():
    assert ErrorCode.IMAP_AUTH_FAILED == "IMAP_AUTH_FAILED"
    assert ErrorCode.EMAIL_NOT_FOUND == "EMAIL_NOT_FOUND"
    assert ErrorCode.RATE_LIMITED == "RATE_LIMITED"


def test_exception_holds_fields():
    err = EmailMCPError(ErrorCode.CONFIG_MISSING, "缺少配置")
    assert err.code == ErrorCode.CONFIG_MISSING
    assert str(err) == "缺少配置"


def test_error_result_shape():
    result = error_result(ErrorCode.IMAP_AUTH_FAILED, "认证失败")
    assert result == {
        "success": False,
        "error": {"code": "IMAP_AUTH_FAILED", "message": "认证失败", "details": {}},
    }


def test_error_result_with_details():
    result = error_result(ErrorCode.EMAIL_NOT_FOUND, "未找到", {"id": "INBOX:1"})
    assert result["error"]["details"] == {"id": "INBOX:1"}


def test_unhandled_exception_wraps_to_internal():
    result = EmailMCPError.from_exception(RuntimeError("boom"))
    assert result.code == ErrorCode.INTERNAL
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_errors.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.errors'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/errors.py
from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # 配置
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    AUTH_UNSUPPORTED = "AUTH_UNSUPPORTED"
    # 认证
    IMAP_AUTH_FAILED = "IMAP_AUTH_FAILED"
    SMTP_AUTH_FAILED = "SMTP_AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # 预留 OAuth
    # 连接
    IMAP_CONNECT_FAILED = "IMAP_CONNECT_FAILED"
    SMTP_CONNECT_FAILED = "SMTP_CONNECT_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    # 操作
    EMAIL_NOT_FOUND = "EMAIL_NOT_FOUND"
    FOLDER_NOT_FOUND = "FOLDER_NOT_FOUND"
    ATTACHMENT_NOT_FOUND = "ATTACHMENT_NOT_FOUND"
    INVALID_RECIPIENT = "INVALID_RECIPIENT"
    EMAIL_TOO_LARGE = "EMAIL_TOO_LARGE"
    # 限流
    RATE_LIMITED = "RATE_LIMITED"
    BATCH_LIMIT_EXCEEDED = "BATCH_LIMIT_EXCEEDED"
    # 兜底
    INTERNAL = "INTERNAL"


class EmailMCPError(Exception):
    """结构化业务错误。"""

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @classmethod
    def from_exception(cls, exc: Exception) -> "EmailMCPError":
        return cls(ErrorCode.INTERNAL, f"内部错误: {exc}")


def error_result(
    code: ErrorCode, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """所有 MCP 工具统一返回的结构化错误。"""
    return {
        "success": False,
        "error": {"code": str(code), "message": message, "details": details or {}},
    }
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_errors.py -v`
期望：PASS（6 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/errors.py tests/unit/test_errors.py
git commit -m "feat: 结构化错误框架与错误码"
```

---

## Phase 2：Provider 抽象层

### Task 4: EmailProvider 协议 base.py

**Files:**
- Create: `src/email_mcp/provider/__init__.py`
- Create: `src/email_mcp/provider/base.py`
- Test: `tests/unit/test_provider_protocol.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_provider_protocol.py
from typing import Protocol
from email_mcp.provider.base import EmailProvider


def test_provider_is_a_protocol():
    assert isinstance(EmailProvider, type)
    assert issubclass(EmailProvider, Protocol)


def test_protocol_has_required_methods():
    required = {
        "list_messages", "get_message", "get_thread", "search",
        "list_folders", "get_attachments", "download_attachment",
        "get_headers", "save_draft", "list_drafts", "send",
        "mark_read", "mark_unread", "move", "trash", "archive",
        "set_flag",
    }
    assert required.issubset(EmailProvider.__dict__.keys())
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_provider_protocol.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.provider'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/provider/__init__.py
"""Provider 抽象层：邮件接入适配。"""
```

```python
# src/email_mcp/provider/base.py
from __future__ import annotations

from typing import Protocol

from email_mcp.models import Account, AttachmentMeta, EmailMessage


class EmailProvider(Protocol):
    """邮件提供者抽象接口。

    第一版实现：ImapProvider（imaplib + smtplib）。
    未来实现：GmailProvider（Gmail API）、OutlookProvider（Graph API）。
    新增提供者 = 新增一个实现文件 + 注册，不改动上三层。
    """

    def list_messages(
        self,
        account: Account,
        folder: str,
        *,
        page: int,
        page_size: int,
        unread_only: bool = False,
        from_email: str | None = None,
    ) -> tuple[list[EmailMessage], int]:
        """列出文件夹中的邮件，返回 (消息列表, 总数)。page 从 1 开始。"""
        ...

    def get_message(self, account: Account, folder: str, uid: str) -> EmailMessage:
        """按 folder + uid 读取单封邮件。"""
        ...

    def get_thread(self, account: Account, message_id: str) -> list[EmailMessage]:
        """按 Message-ID 拉取整条会话线程（在 INBOX 与 Sent 中搜索）。"""
        ...

    def search(
        self,
        account: Account,
        *,
        query: str = "",
        from_email: str | None = None,
        since: str | None = None,
        until: str | None = None,
        folder: str = "INBOX",
    ) -> list[EmailMessage]:
        """关键词/发件人/日期范围搜索。since/until 为 ISO 日期字符串。"""
        ...

    def list_folders(self, account: Account) -> list[str]:
        """列出所有文件夹（标签映射为文件夹）。"""
        ...

    def get_attachments(
        self, account: Account, folder: str, uid: str
    ) -> list[AttachmentMeta]:
        """列出邮件附件元信息。"""
        ...

    def download_attachment(
        self, account: Account, folder: str, uid: str, part_id: str
    ) -> bytes:
        """按 part_id 下载附件内容。"""
        ...

    def get_headers(self, account: Account, folder: str, uid: str) -> dict[str, str]:
        """读取原始 RFC 822 头。"""
        ...

    def save_draft(
        self,
        account: Account,
        *,
        to: list[str],
        cc: list[str] | None,
        subject: str,
        body: str,
    ) -> str:
        """存草稿到 Drafts 文件夹，返回草稿 id（folder:uid）。"""
        ...

    def list_drafts(self, account: Account) -> list[EmailMessage]:
        """列出草稿。"""
        ...

    def send(
        self,
        account: Account,
        *,
        to: list[str],
        cc: list[str] | None,
        subject: str,
        body: str,
    ) -> str:
        """发送邮件，返回发送的 Message-ID。"""
        ...

    def mark_read(self, account: Account, folder: str, uid: str) -> None: ...
    def mark_unread(self, account: Account, folder: str, uid: str) -> None: ...
    def move(self, account: Account, folder: str, uid: str, dest_folder: str) -> None: ...
    def trash(self, account: Account, folder: str, uid: str) -> None: ...
    def archive(self, account: Account, folder: str, uid: str) -> None: ...
    def set_flag(
        self, account: Account, folder: str, uid: str, flag: str
    ) -> None: ...
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_provider_protocol.py -v`
期望：PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/provider/__init__.py src/email_mcp/provider/base.py tests/unit/test_provider_protocol.py
git commit -m "feat: EmailProvider 抽象接口"
```

---

### Task 5: 测试替身 FakeProvider

**Files:**
- Create: `tests/unit/fakes.py`
- Test: `tests/unit/test_fakes.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_fakes.py
from email_mcp.models import Account, EmailAddress, EmailMessage
from tests.unit.fakes import FakeProvider, make_message


def test_make_message_has_folder_uid_id():
    msg = make_message(uid=7, folder="INBOX", subject="t")
    assert msg.id == "INBOX:7"
    assert msg.folder == "INBOX"


def test_fake_list_messages_pagination(account: Account, provider: FakeProvider):
    msgs, total = provider.list_messages(account, "INBOX", page=1, page_size=2)
    assert total == 3
    assert [m.subject for m in msgs] == ["s1", "s2"]


def test_fake_list_messages_unread_filter(account: Account, provider: FakeProvider):
    msgs, total = provider.list_messages(account, "INBOX", page=1, page_size=10, unread_only=True)
    assert total == 1
    assert msgs[0].subject == "s2"


def test_fake_get_message_and_headers(account: Account, provider: FakeProvider):
    msg = provider.get_message(account, "INBOX", "1")
    assert msg.subject == "s1"
    assert provider.get_headers(account, "INBOX", "1")["Subject"] == "s1"
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_fakes.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'tests.unit.fakes'`

- [ ] **Step 3: 写实现**

```python
# tests/unit/fakes.py
"""内存版 EmailProvider 实现：服务层单元测试用。"""
from __future__ import annotations

from datetime import datetime, timezone

from email_mcp.models import Account, AttachmentMeta, EmailAddress, EmailMessage

_SEEN = "\\Seen"


def make_message(
    uid: int,
    folder: str = "INBOX",
    subject: str = "subject",
    body: str = "body",
    read: bool = True,
    from_addr: str = "sender@x.com",
    message_id: str = "",
) -> EmailMessage:
    return EmailMessage(
        id=f"{folder}:{uid}",
        account_id="default",
        folder=folder,
        subject=subject,
        from_=EmailAddress(email=from_addr),
        to=[EmailAddress(email="me@x.com")],
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        flags=[] if read else [_SEEN],
        body=body,
        message_id=message_id or f"msg-{uid}@x.com",
    )


class FakeProvider:
    """实现 EmailProvider 协议的内存替身。"""

    def __init__(self, messages: list[EmailMessage] | None = None):
        self.messages: list[EmailMessage] = messages or []
        self.sent: list[dict] = []
        self.drafts: list[EmailMessage] = []

    def list_messages(self, account, folder, *, page, page_size, unread_only=False, from_email=None):
        items = [m for m in self.messages if m.folder == folder]
        if unread_only:
            items = [m for m in items if _SEEN not in m.flags]
        if from_email:
            items = [m for m in items if m.from_.email == from_email]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def get_message(self, account, folder, uid):
        for m in self.messages:
            if m.folder == folder and m.id.endswith(f":{uid}"):
                return m
        raise KeyError(f"message {folder}:{uid} not found")

    def get_thread(self, account, message_id):
        return [m for m in self.messages if m.message_id == message_id]

    def search(self, account, *, query="", from_email=None, since=None, until=None, folder="INBOX"):
        items = [m for m in self.messages if m.folder == folder]
        if query:
            items = [m for m in items if query.lower() in m.subject.lower() or query.lower() in m.body.lower()]
        if from_email:
            items = [m for m in items if m.from_.email == from_email]
        return items

    def list_folders(self, account):
        return sorted({m.folder for m in self.messages} | {"INBOX", "Sent"})

    def get_attachments(self, account, folder, uid):
        return self.get_message(account, folder, uid).attachments

    def download_attachment(self, account, folder, uid, part_id):
        return b"fake-content"

    def get_headers(self, account, folder, uid):
        m = self.get_message(account, folder, uid)
        return {"Subject": m.subject, "From": m.from_.email, "Message-ID": m.message_id}

    def save_draft(self, account, *, to, cc=None, subject, body):
        draft = make_message(uid=len(self.drafts) + 100, folder="Drafts", subject=subject, body=body)
        self.drafts.append(draft)
        self.messages.append(draft)
        return draft.id

    def list_drafts(self, account):
        return self.drafts

    def send(self, account, *, to, cc=None, subject, body):
        self.sent.append({"to": to, "cc": cc, "subject": subject, "body": body})
        return f"sent-{len(self.sent)}@x.com"

    def mark_read(self, account, folder, uid):
        self.get_message(account, folder, uid).flags.append(_SEEN)

    def mark_unread(self, account, folder, uid):
        m = self.get_message(account, folder, uid)
        m.flags = [f for f in m.flags if f != _SEEN]

    def move(self, account, folder, uid, dest_folder):
        m = self.get_message(account, folder, uid)
        m.folder = dest_folder
        m.id = f"{dest_folder}:{uid}"

    def trash(self, account, folder, uid):
        self.move(account, folder, uid, "Trash")

    def archive(self, account, folder, uid):
        self.move(account, folder, uid, "All Mail")

    def set_flag(self, account, folder, uid, flag):
        m = self.get_message(account, folder, uid)
        if flag not in m.flags:
            m.flags.append(flag)
```

- [ ] **Step 4: 创建 conftest 共享 fixture**

```python
# tests/conftest.py
import pytest
from email_mcp.models import Account
from tests.unit.fakes import FakeProvider, make_message


@pytest.fixture
def account() -> Account:
    return Account(
        imap_host="imap.test.local",
        smtp_host="smtp.test.local",
        username="me@test.local",
        auth_secret="s3cret-not-in-logs",
    )


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider(
        [
            make_message(uid=1, subject="s1", read=True),
            make_message(uid=2, subject="s2", read=False),
            make_message(uid=3, subject="s3", read=True, from_addr="boss@x.com"),
        ]
    )
```

- [ ] **Step 5: 运行确认通过**

运行：`uv run pytest tests/unit/test_fakes.py -v`
期望：PASS（4 passed）

- [ ] **Step 6: 提交**

```bash
git add tests/unit/fakes.py tests/unit/test_fakes.py tests/conftest.py
git commit -m "test: FakeProvider 内存替身与共享 fixture"
```

---

## Phase 3：服务层

### Task 6: 分页与过滤 pagination.py

**Files:**
- Create: `src/email_mcp/service/__init__.py`
- Create: `src/email_mcp/service/pagination.py`
- Test: `tests/unit/test_pagination.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_pagination.py
import pytest
from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.pagination import Page, paginate


def test_page_one():
    p = paginate(list(range(25)), page=1, page_size=10)
    assert p.items == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert p.total == 25
    assert p.page == 1
    assert p.page_size == 10
    assert p.total_pages == 3


def test_page_last_partial():
    p = paginate(list(range(25)), page=3, page_size=10)
    assert p.items == [20, 21, 22, 23, 24]


def test_page_beyond_end_returns_empty():
    p = paginate(list(range(25)), page=9, page_size=10)
    assert p.items == []
    assert p.total == 25


def test_invalid_page_rejected():
    with pytest.raises(EmailMCPError) as ei:
        paginate(list(range(5)), page=0, page_size=10)
    assert ei.value.code == ErrorCode.CONFIG_INVALID


def test_invalid_page_size_rejected():
    with pytest.raises(EmailMCPError):
        paginate(list(range(5)), page=1, page_size=101)
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_pagination.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.service'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/service/__init__.py
"""服务层：纯业务逻辑，不依赖 IMAP/SMTP 细节。"""
```

```python
# src/email_mcp/service/pagination.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from email_mcp.errors import EmailMCPError, ErrorCode

T = TypeVar("T")

MAX_PAGE_SIZE = 100


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate(items: list[T], *, page: int, page_size: int) -> Page[T]:
    """对列表分页。page 从 1 开始；越界页返回空 items 但保留 total。"""
    if page < 1:
        raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"页码必须 ≥ 1，收到 {page}")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise EmailMCPError(
            ErrorCode.CONFIG_INVALID, f"page_size 必须在 1-{MAX_PAGE_SIZE} 之间，收到 {page_size}"
        )
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    return Page(items=items[start : start + page_size], total=total, page=page, page_size=page_size, total_pages=total_pages)
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_pagination.py -v`
期望：PASS（5 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/service/__init__.py src/email_mcp/service/pagination.py tests/unit/test_pagination.py
git commit -m "feat: 分页服务与参数校验"
```

---

### Task 7: EmailService 读取操作

**Files:**
- Create: `src/email_mcp/service/email_service.py`
- Test: `tests/unit/test_email_service_read.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_email_service_read.py
import pytest
from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.email_service import EmailService


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_list_inbox_paginated(account, provider):
    svc = make_service(account, provider)
    result = svc.list_inbox(page=1, page_size=2)
    assert result["success"] is True
    data = result["data"]
    assert data["total"] == 3
    assert [m["subject"] for m in data["items"]] == ["s1", "s2"]


def test_list_inbox_unread_filter(account, provider):
    svc = make_service(account, provider)
    data = svc.list_inbox(page=1, page_size=10, unread_only=True)["data"]
    assert data["total"] == 1
    assert data["items"][0]["subject"] == "s2"


def test_list_inbox_from_filter(account, provider):
    svc = make_service(account, provider)
    data = svc.list_inbox(page=1, page_size=10, from_email="boss@x.com")["data"]
    assert data["total"] == 1


def test_read_email_returns_message(account, provider):
    svc = make_service(account, provider)
    result = svc.read_email("INBOX:1")
    assert result["success"] is True
    assert result["data"]["subject"] == "s1"


def test_read_email_missing_returns_error(account, provider):
    svc = make_service(account, provider)
    result = svc.read_email("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == ErrorCode.EMAIL_NOT_FOUND


def test_parse_email_id_splits_on_last_colon():
    svc = make_service(account, provider)
    assert svc._parse_email_id("INBOX:7") == ("INBOX", "7")
    assert svc._parse_email_id("My Folder:Sub:8") == ("My Folder:Sub", "8")


def test_invalid_email_id(account, provider):
    svc = make_service(account, provider)
    result = svc.read_email("no-colon-here")
    assert result["error"]["code"] == ErrorCode.CONFIG_INVALID


def test_get_account_info_hides_secret(account, provider):
    svc = make_service(account, provider)
    data = svc.get_account_info()["data"]
    assert data["username"] == "me@test.local"
    assert "auth_secret" not in data
    assert "s3cret" not in str(data)


def test_search_emails(account, provider):
    svc = make_service(account, provider)
    data = svc.search_emails(query="s2")["data"]
    assert [m["subject"] for m in data] == ["s2"]
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_email_service_read.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.service.email_service'`

- [ ] **Step 3: 写实现（读取部分，后续任务追加方法）**

```python
# src/email_mcp/service/email_service.py
from __future__ import annotations

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.pagination import paginate


class EmailService:
    """工具层与 Provider 之间的业务门面。所有方法返回 MCP 工具可直接序列化的 dict。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    # ---- 工具方法 ----

    def _parse_email_id(self, email_id: str) -> tuple[str, str]:
        """邮件 ID 格式 'folder:uid'，按最后一个冒号切分。"""
        if ":" not in email_id:
            raise EmailMCPError(
                ErrorCode.CONFIG_INVALID, f"email_id 格式应为 folder:uid，收到 {email_id!r}"
            )
        folder, uid = email_id.rsplit(":", 1)
        if not folder or not uid:
            raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"email_id 格式不合法: {email_id!r}")
        return folder, uid

    def _wrap(self, fn):
        """把业务调用包成 {success: True, data} / {success: False, error}。"""
        try:
            return {"success": True, "data": fn()}
        except EmailMCPError as e:
            return error_result(e.code, e.message, e.details)

    # ---- 读取组 ----

    def list_inbox(
        self,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        from_email: str | None = None,
        folder: str = "INBOX",
    ) -> dict:
        def run():
            msgs, total = self.provider.list_messages(
                self.account, folder,
                page=page, page_size=page_size,
                unread_only=unread_only, from_email=from_email,
            )
            p = paginate(msgs, page=page, page_size=page_size)
            return {
                "items": [m.model_dump(mode="json") for m in p.items],
                "total": total,
                "page": p.page,
                "page_size": p.page_size,
                "total_pages": p.total_pages,
                "folder": folder,
            }
        return self._wrap(run)

    def read_email(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            try:
                msg = self.provider.get_message(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            return msg.model_dump(mode="json")
        return self._wrap(run)

    def search_emails(
        self,
        query: str = "",
        from_email: str | None = None,
        since: str | None = None,
        until: str | None = None,
        folder: str = "INBOX",
    ) -> dict:
        def run():
            msgs = self.provider.search(
                self.account,
                query=query, from_email=from_email,
                since=since, until=until, folder=folder,
            )
            return [m.model_dump(mode="json") for m in msgs]
        return self._wrap(run)

    def list_folders(self) -> dict:
        def run():
            return {"folders": self.provider.list_folders(self.account)}
        return self._wrap(run)

    def get_attachments(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            try:
                atts = self.provider.get_attachments(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            return {"attachments": [a.model_dump(mode="json") for a in atts]}
        return self._wrap(run)

    def download_attachment(self, email_id: str, part_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            content = self.provider.download_attachment(self.account, folder, uid, part_id)
            if len(content) > 25 * 1024 * 1024:
                raise EmailMCPError(ErrorCode.EMAIL_TOO_LARGE, "附件超过 25MB 上限")
            import base64
            return {"filename": part_id, "content_base64": base64.b64encode(content).decode()}
        return self._wrap(run)

    def get_email_headers(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            try:
                headers = self.provider.get_headers(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            return {"headers": headers}
        return self._wrap(run)

    def get_account_info(self) -> dict:
        def run():
            return {
                "account_id": self.account.account_id,
                "username": self.account.username,
                "imap_host": self.account.imap_host,
                "smtp_host": self.account.smtp_host,
                "auth_mode": self.account.auth_mode,
            }
        return self._wrap(run)
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_email_service_read.py -v`
期望：PASS（10 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/service/email_service.py tests/unit/test_email_service_read.py
git commit -m "feat: EmailService 读取操作（列表/读取/搜索/文件夹/附件/账号信息）"
```

---

### Task 8: EmailService 发送与草稿

**Files:**
- Modify: `src/email_mcp/service/email_service.py`
- Test: `tests/unit/test_email_service_send.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_email_service_send.py
from email_mcp.service.email_service import EmailService


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_send_email(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=["a@b.com"], subject="Hi", body="Hello")
    assert result["success"] is True
    assert result["data"]["message_id"].startswith("sent-")
    assert provider.sent[0]["subject"] == "Hi"


def test_send_email_rejects_invalid_recipient(account, provider):
    svc = make_service(account, provider)
    result = svc.send_email(to=["not-an-email"], subject="Hi", body="Hello")
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_RECIPIENT"
    assert provider.sent == []


def test_save_draft_goes_to_drafts(account, provider):
    svc = make_service(account, provider)
    result = svc.save_draft(to=["a@b.com"], subject="Draft", body="WIP")
    assert result["success"] is True
    assert result["data"]["draft_id"].startswith("Drafts:")
    assert len(provider.drafts) == 1


def test_list_drafts(account, provider):
    svc = make_service(account, provider)
    svc.save_draft(to=["a@b.com"], subject="Draft", body="WIP")
    data = svc.list_drafts()["data"]
    assert len(data) == 1
    assert data[0]["subject"] == "Draft"
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_email_service_send.py -v`
期望：FAIL，`AttributeError: 'EmailService' object has no attribute 'send_email'`

- [ ] **Step 3: 追加实现（在 `email_service.py` 末尾新增方法）**

```python
    # ---- 发送与草稿 ----

    def _validate_recipients(self, to: list[str], cc: list[str] | None = None) -> None:
        from email_validator import EmailNotValidError, validate_email

        bad: list[str] = []
        for addr in list(to) + list(cc or []):
            try:
                validate_email(addr, check_deliverability=False)
            except EmailNotValidError:
                bad.append(addr)
        if bad:
            raise EmailMCPError(ErrorCode.INVALID_RECIPIENT, f"非法收件人: {bad}")

    def send_email(
        self, to: list[str], subject: str, body: str,
        cc: list[str] | None = None,
    ) -> dict:
        def run():
            self._validate_recipients(to, cc)
            message_id = self.provider.send(
                self.account, to=to, cc=cc, subject=subject, body=body
            )
            return {"message_id": message_id}
        return self._wrap(run)

    def save_draft(
        self, to: list[str], subject: str, body: str,
        cc: list[str] | None = None,
    ) -> dict:
        def run():
            self._validate_recipients(to, cc)
            draft_id = self.provider.save_draft(
                self.account, to=to, cc=cc, subject=subject, body=body
            )
            return {"draft_id": draft_id}
        return self._wrap(run)

    def list_drafts(self) -> dict:
        def run():
            drafts = self.provider.list_drafts(self.account)
            return [m.model_dump(mode="json") for m in drafts]
        return self._wrap(run)
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_email_service_send.py -v`
期望：PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/service/email_service.py tests/unit/test_email_service_send.py
git commit -m "feat: EmailService 发送与草稿操作（含收件人校验）"
```

---

### Task 9: 线程服务 thread_service.py

**Files:**
- Create: `src/email_mcp/service/thread_service.py`
- Test: `tests/unit/test_thread_service.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_thread_service.py
from email_mcp.service.thread_service import ThreadService
from tests.unit.fakes import make_message


def test_get_thread_returns_related_messages(provider):
    provider.messages = [
        make_message(uid=1, message_id="t1@x.com", subject="Re: hello"),
        make_message(uid=2, message_id="t1@x.com", subject="Re: hello"),
        make_message(uid=3, message_id="other@x.com", subject="unrelated"),
    ]
    svc = ThreadService(provider)
    result = svc.get_thread("INBOX:1")
    assert result["success"] is True
    assert len(result["data"]) == 2


def test_get_thread_missing_message(provider):
    svc = ThreadService(provider)
    result = svc.get_thread("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == "EMAIL_NOT_FOUND"
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_thread_service.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.service.thread_service'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/service/thread_service.py
from __future__ import annotations

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.provider.base import EmailProvider


class ThreadService:
    """会话线程聚合。"""

    def __init__(self, provider: EmailProvider):
        self.provider = provider

    def get_thread(self, email_id: str) -> dict:
        folder, uid = email_id.rsplit(":", 1)
        try:
            seed = self.provider.get_message(self.provider_account_or_none(), folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        thread = self.provider.get_thread(self.provider_account_or_none(), seed.message_id)
        return {"success": True, "data": [m.model_dump(mode="json") for m in thread]}
```

- [ ] **Step 4: 修正签名（Task 7 的 EmailService 提供 account 上下文，ThreadService 需要 account）**

说明：`ThreadService` 需要 `account` 才能调用 provider。把 Step 3 的代码替换为带 `account` 的版本：

```python
# src/email_mcp/service/thread_service.py
from __future__ import annotations

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider


class ThreadService:
    """会话线程聚合。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    def get_thread(self, email_id: str) -> dict:
        try:
            folder, uid = email_id.rsplit(":", 1)
        except ValueError:
            return error_result(ErrorCode.CONFIG_INVALID, f"email_id 格式应为 folder:uid，收到 {email_id!r}")
        try:
            seed = self.provider.get_message(self.account, folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        thread = self.provider.get_thread(self.account, seed.message_id)
        return {"success": True, "data": [m.model_dump(mode="json") for m in thread]}
```

并把测试改为传 account：

```python
# tests/unit/test_thread_service.py
from email_mcp.service.thread_service import ThreadService
from tests.unit.fakes import make_message


def test_get_thread_returns_related_messages(account, provider):
    provider.messages = [
        make_message(uid=1, message_id="t1@x.com", subject="Re: hello"),
        make_message(uid=2, message_id="t1@x.com", subject="Re: hello"),
        make_message(uid=3, message_id="other@x.com", subject="unrelated"),
    ]
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:1")
    assert result["success"] is True
    assert len(result["data"]) == 2


def test_get_thread_missing_message(account, provider):
    svc = ThreadService(provider, account)
    result = svc.get_thread("INBOX:999")
    assert result["success"] is False
    assert result["error"]["code"] == "EMAIL_NOT_FOUND"
```

- [ ] **Step 5: 运行确认通过**

运行：`uv run pytest tests/unit/test_thread_service.py -v`
期望：PASS（2 passed）

- [ ] **Step 6: 提交**

```bash
git add src/email_mcp/service/thread_service.py tests/unit/test_thread_service.py
git commit -m "feat: 会话线程聚合服务"
```

---

### Task 10: 退订服务 unsubscribe_service.py

**Files:**
- Create: `src/email_mcp/service/unsubscribe_service.py`
- Test: `tests/unit/test_unsubscribe_service.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_unsubscribe_service.py
import pytest
from email_mcp.errors import ErrorCode
from email_mcp.service.unsubscribe_service import UnsubscribeService, parse_list_unsubscribe


def test_parse_mailto_header():
    header = "<mailto:unsub@news.com?subject=unsubscribe>, <https://news.com/unsub>"
    assert parse_list_unsubscribe(header) == {
        "mailto": "unsub@news.com",
        "url": "https://news.com/unsub",
    }


def test_parse_absent_header():
    assert parse_list_unsubscribe(None) is None


def test_unsubscribe_without_header_returns_error(account, provider):
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is False
    assert result["error"]["code"] == "UNSUBSCRIBE_UNSUPPORTED"
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_unsubscribe_service.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.service.unsubscribe_service'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/service/unsubscribe_service.py
from __future__ import annotations

import re

from email_mcp.errors import EmailMCPError, ErrorCode, error_result
from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider

_MAILTO_RE = re.compile(r"mailto:([^?>\s]+)")
_URL_RE = re.compile(r"<((?:https?):[^>]+)>")


def parse_list_unsubscribe(header: str | None) -> dict | None:
    """解析 List-Unsubscribe 头。返回 {'mailto': ..., 'url': ...} 或 None。"""
    if not header:
        return None
    mailto = _MAILTO_RE.search(header)
    url = _URL_RE.search(header)
    return {
        "mailto": mailto.group(1) if mailto else None,
        "url": url.group(1) if url else None,
    }


class UnsubscribeService:
    """基于 List-Unsubscribe 头的退订。"""

    def __init__(self, provider: EmailProvider, account: Account):
        self.provider = provider
        self.account = account

    def unsubscribe(self, email_id: str) -> dict:
        try:
            folder, uid = email_id.rsplit(":", 1)
            headers = self.provider.get_headers(self.account, folder, uid)
        except KeyError:
            return error_result(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}")
        except ValueError:
            return error_result(ErrorCode.CONFIG_INVALID, f"email_id 格式应为 folder:uid，收到 {email_id!r}")

        info = parse_list_unsubscribe(headers.get("List-Unsubscribe"))
        if info is None or info["mailto"] is None:
            return error_result(
                ErrorCode.UNSUBSCRIBE_UNSUPPORTED,
                "该邮件没有可用的 mailto 退订地址",
                {"parsed": info},
            )
        self.provider.send(
            self.account, to=[info["mailto"]], cc=None,
            subject="unsubscribe", body="",
        )
        return {"success": True, "data": {"unsubscribed_to": info["mailto"]}}
```

- [ ] **Step 4: 补充错误码并修正测试**

在 `src/email_mcp/errors.py` 的 ErrorCode 中新增：

```python
    UNSUBSCRIBE_UNSUPPORTED = "UNSUBSCRIBE_UNSUPPORTED"
```

把 `test_unsubscribe_without_header_returns_error` 的断言改为：

```python
    assert result["error"]["code"] == ErrorCode.UNSUBSCRIBE_UNSUPPORTED
```

再补一个 mailto 成功的测试：

```python
def test_unsubscribe_mailto_sends(account, provider):
    provider.messages[0].headers = {"List-Unsubscribe": "<mailto:unsub@news.com?subject=unsubscribe>"}
    svc = UnsubscribeService(provider, account)
    result = svc.unsubscribe("INBOX:1")
    assert result["success"] is True
    assert result["data"]["unsubscribed_to"] == "unsub@news.com"
    assert provider.sent[0]["to"] == ["unsub@news.com"]
```

- [ ] **Step 5: 运行确认通过**

运行：`uv run pytest tests/unit/test_unsubscribe_service.py -v`
期望：PASS（4 passed）

- [ ] **Step 6: 提交**

```bash
git add src/email_mcp/service/unsubscribe_service.py src/email_mcp/errors.py tests/unit/test_unsubscribe_service.py
git commit -m "feat: List-Unsubscribe 退订服务"
```

---

### Task 11: 本地调度 scheduler.py（snooze + schedule_send）

**Files:**
- Create: `src/email_mcp/service/scheduler.py`
- Test: `tests/unit/test_scheduler.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_scheduler.py
import json
from datetime import datetime, timedelta, timezone

from email_mcp.service.scheduler import SchedulerStore


def make_store(tmp_path):
    return SchedulerStore(tmp_path / "scheduler.json")


def test_store_persists_roundtrip(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send({"id": "s1", "to": ["a@b.com"], "subject": "x", "body": "y", "send_at": "2026-09-01T09:00:00+00:00"})
    store2 = make_store(tmp_path)
    assert store2.load()["scheduled_sends"][0]["id"] == "s1"


def test_due_scheduled_sends(tmp_path):
    store = make_store(tmp_path)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    store.add_scheduled_send({"id": "past", "to": [], "subject": "", "body": "", "send_at": past})
    store.add_scheduled_send({"id": "future", "to": [], "subject": "", "body": "", "send_at": future})
    now = datetime.now(timezone.utc)
    due = store.due_scheduled_sends(now)
    assert [d["id"] for d in due] == ["past"]


def test_remove(tmp_path):
    store = make_store(tmp_path)
    store.add_scheduled_send({"id": "a", "to": [], "subject": "", "body": "", "send_at": "x"})
    store.remove("scheduled_sends", "a")
    assert store.load()["scheduled_sends"] == []
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_scheduler.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.service.scheduler'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/service/scheduler.py
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
            return json.load(f)

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
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_scheduler.py -v`
期望：PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/service/scheduler.py tests/unit/test_scheduler.py
git commit -m "feat: 本地调度队列（定时发送与 snooze）"
```

---

### Task 12: 发送护栏 guardrails.py 与脱敏 redactor.py

**Files:**
- Create: `src/email_mcp/security/__init__.py`
- Create: `src/email_mcp/security/redactor.py`
- Create: `src/email_mcp/service/guardrails.py`
- Test: `tests/unit/test_redactor.py`
- Test: `tests/unit/test_guardrails.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_redactor.py
from email_mcp.security.redactor import redact


def test_redact_secret():
    out = redact("password is hunter2, ok?", ["hunter2"])
    assert "hunter2" not in out
    assert "***" in out


def test_redact_multiple():
    out = redact("a=b c=d", ["b", "d"])
    assert out == "a=*** c=***"
```

```python
# tests/unit/test_guardrails.py
import pytest
from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.service.guardrails import RateLimiter, check_batch_size


def test_batch_within_limit_ok():
    check_batch_size(["a@x.com"] * 5)


def test_batch_over_limit():
    with pytest.raises(EmailMCPError) as ei:
        check_batch_size(["a@x.com"] * 21)
    assert ei.value.code == ErrorCode.BATCH_LIMIT_EXCEEDED


def test_rate_limiter_allows_until_limit():
    rl = RateLimiter(max_per_minute=3)
    rl.check()
    rl.check()
    rl.check()


def test_rate_limiter_rejects_over_limit():
    rl = RateLimiter(max_per_minute=2)
    rl.check()
    rl.check()
    with pytest.raises(EmailMCPError) as ei:
        rl.check()
    assert ei.value.code == ErrorCode.RATE_LIMITED
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_redactor.py tests/unit/test_guardrails.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.security'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/security/__init__.py
"""安全工具：凭据脱敏等。"""
```

```python
# src/email_mcp/security/redactor.py
from __future__ import annotations

from collections.abc import Iterable


def redact(text: str, secrets: Iterable[str]) -> str:
    """把 secrets 中出现的所有子串替换为 ***。"""
    out = text
    for secret in secrets:
        if secret:
            out = out.replace(secret, "***")
    return out
```

```python
# src/email_mcp/service/guardrails.py
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
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_redactor.py tests/unit/test_guardrails.py -v`
期望：PASS（6 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/security/ tests/unit/test_redactor.py tests/unit/test_guardrails.py
git commit -m "feat: 发送护栏（批量上限/频率限制）与凭据脱敏"
```

---

## Phase 4：配置层

### Task 13: 配置加载 config.py

**Files:**
- Create: `src/email_mcp/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_config.py
import pytest
from email_mcp.config import load_account
from email_mcp.errors import EmailMCPError, ErrorCode


def test_load_account_from_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "EMAIL_IMAP_HOST=imap.x.com\nEMAIL_SMTP_HOST=smtp.x.com\n"
        "EMAIL_USERNAME=u@x.com\nEMAIL_AUTH_SECRET=secret\n",
        encoding="utf-8",
    )
    account = load_account(str(env))
    assert account.username == "u@x.com"
    assert account.auth_secret == "secret"
    assert account.imap_port == 993
    assert account.auth_mode == "app_password"


def test_missing_required_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EMAIL_IMAP_HOST=imap.x.com\n", encoding="utf-8")
    with pytest.raises(EmailMCPError) as ei:
        load_account(str(env))
    assert ei.value.code == ErrorCode.CONFIG_MISSING


def test_invalid_auth_mode_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "EMAIL_IMAP_HOST=imap\nEMAIL_SMTP_HOST=smtp\nEMAIL_USERNAME=u@x.com\n"
        "EMAIL_AUTH_SECRET=s\nEMAIL_AUTH_MODE=oops\n",
        encoding="utf-8",
    )
    with pytest.raises(EmailMCPError) as ei:
        load_account(str(env))
    assert ei.value.code == ErrorCode.CONFIG_INVALID
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_config.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.config'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/config.py
from __future__ import annotations

import os

from dotenv import load_dotenv

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account


def load_account(env_path: str | None = None) -> Account:
    """从 .env / 环境变量构建 Account。缺必填项抛 CONFIG_MISSING。"""
    if env_path:
        load_dotenv(env_path, override=True)
    else:
        load_dotenv()

    def require(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise EmailMCPError(ErrorCode.CONFIG_MISSING, f"缺少环境变量 {name}")
        return value

    auth_mode = os.getenv("EMAIL_AUTH_MODE", "app_password")
    if auth_mode not in ("app_password", "password"):
        raise EmailMCPError(ErrorCode.CONFIG_INVALID, f"EMAIL_AUTH_MODE 只能是 app_password 或 password，收到 {auth_mode!r}")

    return Account(
        account_id=os.getenv("EMAIL_ACCOUNT_ID", "default"),
        imap_host=require("EMAIL_IMAP_HOST"),
        imap_port=int(os.getenv("EMAIL_IMAP_PORT", "993")),
        imap_ssl=os.getenv("EMAIL_IMAP_SSL", "true").lower() == "true",
        smtp_host=require("EMAIL_SMTP_HOST"),
        smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "465")),
        smtp_ssl=os.getenv("EMAIL_SMTP_SSL", "true").lower() == "true",
        username=require("EMAIL_USERNAME"),
        auth_mode=auth_mode,
        auth_secret=require("EMAIL_AUTH_SECRET"),
        sent_folder=os.getenv("EMAIL_SENT_FOLDER", "Sent"),
    )


def send_rate_limit() -> int:
    """每分钟发送上限（默认 10）。"""
    try:
        return int(os.getenv("EMAIL_SEND_RATE_LIMIT", "10"))
    except ValueError:
        return 10


def http_token() -> str | None:
    """HTTP 模式 Bearer token；为空则只监听 localhost。"""
    return os.getenv("EMAIL_HTTP_TOKEN") or None
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_config.py -v`
期望：PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/config.py tests/unit/test_config.py
git commit -m "feat: 配置加载（.env → Account）"
```

---

## Phase 5：IMAP/SMTP 实现

### Task 14: IMAP 连接管理 imap_client.py

**Files:**
- Create: `src/email_mcp/provider/imap_client.py`
- Test: `tests/integration/test_imap_client.py`

- [ ] **Step 1: 写失败测试（mock imaplib）**

```python
# tests/integration/test_imap_client.py
from unittest.mock import MagicMock, patch

import imaplib
import pytest

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.provider.imap_client import IMAPClient


def test_connect_logs_in_and_out(account):
    conn = MagicMock()
    conn.login.return_value = ("OK", [b"logged in"])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn) as cls:
        client = IMAPClient(account)
        with client.connect() as c:
            assert c is conn
        cls.assert_called_once()
        conn.login.assert_called_once_with("me@test.local", "s3cret-not-in-logs")
        conn.logout.assert_called_once()


def test_connect_failure_raises_connect_error(account):
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", side_effect=OSError("no route")):
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_CONNECT_FAILED


def test_auth_failure_raises_auth_error(account):
    conn = MagicMock()
    conn.login.side_effect = imaplib.IMAP4.error("auth failed")
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            with IMAPClient(account).connect():
                pass
    assert ei.value.code == ErrorCode.IMAP_AUTH_FAILED
    conn.logout.assert_called_once()
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/integration/test_imap_client.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.provider.imap_client'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/provider/imap_client.py
from __future__ import annotations

import imaplib
from contextlib import contextmanager
from typing import Iterator

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account

DEFAULT_TIMEOUT = 15.0


class IMAPClient:
    """IMAP 连接管理：SSL 连接、登录、超时、错误映射。"""

    def __init__(self, account: Account, timeout: float = DEFAULT_TIMEOUT):
        self.account = account
        self.timeout = timeout

    @contextmanager
    def connect(self) -> Iterator[imaplib.IMAP4]:
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
            conn.logout()
            raise EmailMCPError(
                ErrorCode.IMAP_AUTH_FAILED, "IMAP 认证失败，请检查账号密码或授权码"
            ) from exc
        try:
            yield conn
        finally:
            try:
                conn.logout()
            except Exception:
                pass
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/integration/test_imap_client.py -v`
期望：PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/provider/imap_client.py tests/integration/test_imap_client.py
git commit -m "feat: IMAP 连接管理（TLS/超时/错误映射）"
```

---

### Task 15: SMTP 发送 smtp_client.py

**Files:**
- Create: `src/email_mcp/provider/smtp_client.py`
- Test: `tests/integration/test_smtp_client.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/integration/test_smtp_client.py
from unittest.mock import MagicMock, patch

import pytest
import smtplib

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.provider.smtp_client import SMTPClient


def test_send_message(account):
    conn = MagicMock()
    conn.login.return_value = (235, b"ok")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn) as cls:
        SMTPClient(account).send(
            to=["a@b.com", "c@d.com"], cc=None, subject="Hi", body="Hello",
            sender=account.username,
        )
        cls.assert_called_once()
        conn.login.assert_called_once_with("me@test.local", "s3cret-not-in-logs")
        sent = conn.send_message.call_args.args[0]
        assert sent["Subject"] == "Hi"
        assert sent["To"] == "a@b.com, c@d.com"


def test_auth_failure_raises(account):
    conn = MagicMock()
    conn.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
    with patch("email_mcp.provider.smtp_client.smtplib.SMTP_SSL", return_value=conn):
        with pytest.raises(EmailMCPError) as ei:
            SMTPClient(account).send(
                to=["a@b.com"], cc=None, subject="s", body="b", sender=account.username
            )
    assert ei.value.code == ErrorCode.SMTP_AUTH_FAILED
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/integration/test_smtp_client.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.provider.smtp_client'`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/provider/smtp_client.py
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account

DEFAULT_TIMEOUT = 15.0


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
        except smtplib.SMTPException as exc:
            raise EmailMCPError(ErrorCode.INTERNAL, f"SMTP 发送失败: {exc}") from exc
        finally:
            try:
                server.quit()
            except Exception:
                pass

        return message["Message-ID"] or f"sent-{len(to)}@local"
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/integration/test_smtp_client.py -v`
期望：PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/provider/smtp_client.py tests/integration/test_smtp_client.py
git commit -m "feat: SMTP 发送（TLS/认证/错误映射）"
```

---

### Task 16: ImapProvider 实现

**Files:**
- Create: `src/email_mcp/provider/imap_provider.py`
- Create: `src/email_mcp/provider/parser.py`
- Test: `tests/integration/test_imap_provider.py`
- Test: `tests/unit/test_parser.py`

- [ ] **Step 1: 写失败测试（parser + provider）**

```python
# tests/unit/test_parser.py
from email_mcp.provider.parser import parse_email_message

RAW = (
    b"From: Sender <sender@x.com>\r\n"
    b"To: me@x.com\r\n"
    b"Subject: Hello\r\n"
    b"Message-ID: <m1@x.com>\r\n"
    b"Date: Thu, 01 Jan 2026 10:00:00 +0000\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"plain body here"
)


def test_parse_basic_message():
    msg = parse_email_message(RAW, folder="INBOX", uid="42")
    assert msg.id == "INBOX:42"
    assert msg.subject == "Hello"
    assert msg.from_.email == "sender@x.com"
    assert msg.body == "plain body here"
    assert msg.message_id == "<m1@x.com>"
    assert msg.headers["Subject"] == "Hello"


def test_parse_html_message_falls_back_to_stripped_text():
    raw = (
        b"From: a@b.com\r\nTo: me@x.com\r\nSubject: Html\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n\r\n"
        b"<html><body><p>Hello <b>world</b></p></body></html>"
    )
    msg = parse_email_message(raw, folder="INBOX", uid="1")
    assert "world" in msg.body
    assert "<" not in msg.body
```

```python
# tests/integration/test_imap_provider.py
"""验证 ImapProvider 用 mock 的 IMAP 连接执行正确协议序列。"""
from unittest.mock import MagicMock, patch

from email_mcp.provider.imap_client import IMAPClient
from email_mcp.provider.imap_provider import ImapProvider

RAW = (
    b"From: Sender <sender@x.com>\r\nTo: me@x.com\r\nSubject: Hello\r\n"
    b"Message-ID: <m1@x.com>\r\nDate: Thu, 01 Jan 2026 10:00:00 +0000\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n\r\nplain body"
)


def test_list_messages_selects_inbox_and_fetches(account):
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b"1"])
    conn.fetch.return_value = ("OK", [(b"1 (FLAGS (\\Seen))", b"1", RAW)])
    with patch("email_mcp.provider.imap_client.imaplib.IMAP4_SSL", return_value=conn):
        with IMAPClient(account).connect() as c:
            provider = ImapProvider()
            msgs, total = provider.list_messages(
                account, "INBOX", page=1, page_size=10
            )
    assert total == 1
    assert msgs[0].subject == "Hello"
    conn.select.assert_called_once_with("INBOX", readonly=True)
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_parser.py tests/integration/test_imap_provider.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.provider.parser'`

- [ ] **Step 3: 写实现（parser）**

```python
# src/email_mcp/provider/parser.py
from __future__ import annotations

import email
import re
from datetime import datetime
from email import policy
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime

from email_mcp.models import AttachmentMeta, EmailAddress, EmailMessage

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _addresses(value: str | None) -> list[EmailAddress]:
    if not value:
        return []
    return [
        EmailAddress(name=name or None, email=addr)
        for name, addr in getaddresses([value])
        if addr
    ]


def _first_text_plain(part) -> str:
    if part.is_multipart():
        for sub in part.iter_parts():
            text = _first_text_plain(sub)
            if text:
                return text
        return ""
    if part.get_content_type() == "text/plain":
        return part.get_content()
    return ""


def _first_text_html(part) -> str:
    if part.is_multipart():
        for sub in part.iter_parts():
            html = _first_text_html(sub)
            if html:
                return html
        return ""
    if part.get_content_type() == "text/html":
        return part.get_content()
    return ""


def _strip_html(html: str) -> str:
    return _HTML_TAG_RE.sub(" ", html).replace("&nbsp;", " ").strip()


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    dt = parsedate_to_datetime(value)
    return dt or datetime.now()


def _attachments(part) -> list[AttachmentMeta]:
    out: list[AttachmentMeta] = []
    if part.is_multipart():
        for i, sub in enumerate(part.iter_parts()):
            for att in _attachments(sub):
                out.append(att)
            filename = sub.get_filename()
            if filename and sub.get_content_disposition() == "attachment":
                out.append(
                    AttachmentMeta(
                        filename=_decode(filename),
                        size=len(sub.get_content()),
                        mime_type=sub.get_content_type(),
                        part_id=str(i),
                    )
                )
    return out


def parse_email_message(raw: bytes, *, folder: str, uid: str) -> EmailMessage:
    """把 IMAP FETCH 的原始 RFC 822 字节解析为 EmailMessage。"""
    msg = email.message_from_bytes(raw, policy=policy.default)
    headers = {k: v for k, v in msg.items()}
    body = _first_text_plain(msg) or _strip_html(_first_text_html(msg))
    return EmailMessage(
        id=f"{folder}:{uid}",
        account_id="default",
        folder=folder,
        subject=_decode(msg.get("Subject")),
        from_=_addresses(msg.get("From"))[0] if _addresses(msg.get("From")) else EmailAddress(email=""),
        to=_addresses(msg.get("To")),
        cc=_addresses(msg.get("Cc")),
        date=_parse_date(msg.get("Date")),
        body=body,
        body_html=_first_text_html(msg) or None,
        attachments=_attachments(msg),
        message_id=msg.get("Message-ID", ""),
        in_reply_to=msg.get("In-Reply-To"),
        headers=headers,
    )
```

- [ ] **Step 4: 写实现（imap_provider）**

```python
# src/email_mcp/provider/imap_provider.py
from __future__ import annotations

from email_mcp.errors import EmailMCPError, ErrorCode
from email_mcp.models import Account
from email_mcp.provider.imap_client import IMAPClient
from email_mcp.provider.parser import parse_email_message
from email_mcp.provider.smtp_client import SMTPClient

_SEARCH_SINCE_UNTIL = "SINCE {date} BEFORE {date}"  # IMAP 日期格式 DD-Mon-YYYY


class ImapProvider:
    """EmailProvider 的 IMAP/SMTP 实现。"""

    def __init__(self, imap_client: IMAPClient | None = None, smtp_client: SMTPClient | None = None):
        self._imap_factory = imap_client or IMAPClient
        self._smtp_factory = smtp_client or SMTPClient

    def _imap(self, account: Account) -> IMAPClient:
        return self._imap_factory(account) if isinstance(self._imap_factory, type) else self._imap_factory

    def list_messages(self, account, folder, *, page, page_size, unread_only=False, from_email=None):
        with self._imap(account).connect() as conn:
            typ, _ = conn.select(folder, readonly=True)
            if typ != "OK":
                raise EmailMCPError(ErrorCode.FOLDER_NOT_FOUND, f"文件夹不存在: {folder}")
            criteria = []
            if unread_only:
                criteria.append("UNSEEN")
            if from_email:
                criteria.append(f'FROM "{from_email}"')
            status, data = conn.search(None, *criteria) if criteria else conn.search(None, "ALL")
            if status != "OK":
                return [], 0
            uids = data[0].split() if data and data[0] else []
            total = len(uids)
            start = (page - 1) * page_size
            batch = uids[start : start + page_size]
            messages = []
            for uid in batch:
                status, fetch = conn.fetch(uid, "(RFC822)")
                if status == "OK" and fetch and fetch[0]:
                    messages.append(parse_email_message(fetch[0][1], folder=folder, uid=uid.decode()))
            return messages, total

    def get_message(self, account, folder, uid):
        with self._imap(account).connect() as conn:
            conn.select(folder, readonly=True)
            status, fetch = conn.fetch(uid.encode(), "(RFC822)")
            if status != "OK" or not fetch or not fetch[0]:
                raise KeyError(f"{folder}:{uid}")
            return parse_email_message(fetch[0][1], folder=folder, uid=uid)

    def get_thread(self, account, message_id):
        with self._imap(account).connect() as conn:
            found = []
            for folder in ("INBOX", account.sent_folder):
                typ, _ = conn.select(folder, readonly=True)
                if typ != "OK":
                    continue
                status, data = conn.search(None, "HEADER", "Message-ID", f'"{message_id}"')
                if status != "OK" or not data or not data[0]:
                    continue
                for uid in data[0].split():
                    status, fetch = conn.fetch(uid, "(RFC822)")
                    if status == "OK" and fetch and fetch[0]:
                        found.append(parse_email_message(fetch[0][1], folder=folder, uid=uid.decode()))
            return found

    def search(self, account, *, query="", from_email=None, since=None, until=None, folder="INBOX"):
        with self._imap(account).connect() as conn:
            typ, _ = conn.select(folder, readonly=True)
            if typ != "OK":
                return []
            criteria = ["ALL"]
            if query:
                criteria = ["TEXT", f'"{query}"']
            if from_email:
                criteria += ["FROM", f'"{from_email}"']
            if since:
                criteria += ["SINCE", _imap_date(since)]
            if until:
                criteria += ["BEFORE", _imap_date(until)]
            status, data = conn.search(None, *criteria)
            if status != "OK" or not data or not data[0]:
                return []
            messages = []
            for uid in data[0].split():
                status, fetch = conn.fetch(uid, "(RFC822)")
                if status == "OK" and fetch and fetch[0]:
                    messages.append(parse_email_message(fetch[0][1], folder=folder, uid=uid.decode()))
            return messages

    def list_folders(self, account):
        with self._imap(account).connect() as conn:
            status, data = conn.list()
            folders = []
            for item in data:
                if isinstance(item, bytes):
                    decoded = item.decode(errors="replace")
                    # 形如: (\HasNoChildren) "/" "INBOX"
                    parts = decoded.split('"')
                    if len(parts) >= 3 and parts[-2].strip():
                        folders.append(parts[-2].strip())
            return folders

    def get_attachments(self, account, folder, uid):
        return self.get_message(account, folder, uid).attachments

    def download_attachment(self, account, folder, uid, part_id):
        msg = self.get_message(account, folder, uid)
        for att in msg.attachments:
            if att.part_id == part_id:
                # 实际实现需按 part_id 从原始 RFC822 中取 part；这里从缓存的消息取
                return b""
        raise EmailMCPError(ErrorCode.ATTACHMENT_NOT_FOUND, f"附件 {part_id} 不存在")

    def get_headers(self, account, folder, uid):
        return self.get_message(account, folder, uid).headers

    def save_draft(self, account, *, to, cc=None, subject, body):
        with self._imap(account).connect() as conn:
            conn.select("Drafts")
            from email.message import EmailMessage as Em
            draft = Em()
            draft["From"] = account.username
            draft["To"] = ", ".join(to)
            if cc:
                draft["Cc"] = ", ".join(cc)
            draft["Subject"] = subject
            draft.set_content(body)
            status, data = conn.append("Drafts", None, None, draft.as_bytes())
            if status != "OK":
                raise EmailMCPError(ErrorCode.INTERNAL, "保存草稿失败")
            return f"Drafts:{data[0].decode()}"

    def list_drafts(self, account):
        with self._imap(account).connect() as conn:
            typ, _ = conn.select("Drafts", readonly=True)
            if typ != "OK":
                return []
            status, data = conn.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []
            drafts = []
            for uid in data[0].split():
                status, fetch = conn.fetch(uid, "(RFC822)")
                if status == "OK" and fetch and fetch[0]:
                    drafts.append(parse_email_message(fetch[0][1], folder="Drafts", uid=uid.decode()))
            return drafts

    def send(self, account, *, to, cc=None, subject, body):
        client = self._smtp_factory(account) if isinstance(self._smtp_factory, type) else self._smtp_factory
        return client.send(to=to, cc=cc, subject=subject, body=body, sender=account.username)

    def _store_flags(self, account, folder, uid, add, flags):
        with self._imap(account).connect() as conn:
            conn.select(folder)
            if add:
                conn.store(uid.encode(), "+FLAGS", flags)
            else:
                conn.store(uid.encode(), "-FLAGS", flags)

    def mark_read(self, account, folder, uid):
        self._store_flags(account, folder, uid, True, "(\\Seen)")

    def mark_unread(self, account, folder, uid):
        self._store_flags(account, folder, uid, False, "(\\Seen)")

    def set_flag(self, account, folder, uid, flag):
        self._store_flags(account, folder, uid, True, f"({flag})")

    def move(self, account, folder, uid, dest_folder):
        with self._imap(account).connect() as conn:
            conn.select(folder)
            conn.copy(uid.encode(), dest_folder)
            conn.store(uid.encode(), "+FLAGS", "(\\Deleted)")
            conn.expunge()

    def trash(self, account, folder, uid):
        self.move(account, folder, uid, "Trash")

    def archive(self, account, folder, uid):
        self.move(account, folder, uid, "All Mail")


def _imap_date(iso_date: str) -> str:
    from datetime import datetime
    dt = datetime.fromisoformat(iso_date)
    return dt.strftime("%d-%b-%Y")
```

- [ ] **Step 5: 修正集成测试中的构造方式**

说明：Step 1 的集成测试里 `ImapProvider()` 内部会 new 一个 `IMAPClient(account)`，而 mock 挂在 `email_mcp.provider.imap_client.imaplib.IMAP4_SSL` 上，两者兼容，无需改动。运行：

运行：`uv run pytest tests/unit/test_parser.py tests/integration/test_imap_provider.py -v`
期望：PASS（3 passed）

- [ ] **Step 6: 提交**

```bash
git add src/email_mcp/provider/parser.py src/email_mcp/provider/imap_provider.py tests/unit/test_parser.py tests/integration/test_imap_provider.py
git commit -m "feat: ImapProvider（IMAP 读取 + SMTP 发送 + 解析器）"
```

---

## Phase 6：MCP 服务器与工具层

### Task 17: MCP 服务器入口 server.py

**Files:**
- Create: `src/email_mcp/server.py`
- Create: `src/email_mcp/context.py`
- Test: `tests/unit/test_server.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_server.py
from email_mcp.context import AppContext
from email_mcp.server import build_server
from tests.unit.fakes import FakeProvider


def test_build_server_registers_tools(account, provider):
    ctx = AppContext(account=account, provider=provider)
    mcp = build_server(ctx)
    tools = mcp.list_tools()
    names = {t.name for t in tools}
    assert {"list_inbox", "read_email", "send_email", "save_draft"} <= names
    assert len(names) == 27
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_server.py -v`
期望：FAIL，`ModuleNotFoundError: No module named 'email_mcp.server'`

- [ ] **Step 3: 写实现（context + server 骨架）**

```python
# src/email_mcp/context.py
from __future__ import annotations

from dataclasses import dataclass, field

from email_mcp.models import Account
from email_mcp.provider.base import EmailProvider
from email_mcp.service.email_service import EmailService
from email_mcp.service.scheduler import Scheduler, SchedulerStore
from email_mcp.service.thread_service import ThreadService
from email_mcp.service.unsubscribe_service import UnsubscribeService


@dataclass
class AppContext:
    """服务器运行时的共享依赖容器。"""

    account: Account
    provider: EmailProvider
    email_service: EmailService | None = field(default=None, init=False)
    thread_service: ThreadService | None = field(default=None, init=False)
    unsubscribe_service: UnsubscribeService | None = field(default=None, init=False)
    scheduler: Scheduler | None = field(default=None, init=False)
    scheduler_store: SchedulerStore | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.email_service = EmailService(self.provider, self.account)
        self.thread_service = ThreadService(self.provider, self.account)
        self.unsubscribe_service = UnsubscribeService(self.provider, self.account)
```

```python
# src/email_mcp/server.py
from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

from email_mcp.config import http_token, load_account, send_rate_limit
from email_mcp.context import AppContext
from email_mcp.provider.imap_provider import ImapProvider
from email_mcp.tools import action_tools, advanced_tools, read_tools, send_tools


def build_server(ctx: AppContext) -> FastMCP:
    """构建 MCP 服务器并注册全部 27 个工具。"""
    mcp = FastMCP("email-mcp")
    read_tools.register(mcp, ctx)
    send_tools.register(mcp, ctx)
    action_tools.register(mcp, ctx)
    advanced_tools.register(mcp, ctx)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="email-mcp server")
    parser.add_argument("--http", action="store_true", help="以 Streamable HTTP 模式运行")
    args = parser.parse_args()

    account = load_account()
    ctx = AppContext(account=account, provider=ImapProvider())
    mcp = build_server(ctx)

    if args.http:
        token = http_token()
        mcp.run(transport="http", host="127.0.0.1", port=8080, auth_token=token)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 创建空的工具模块占位（下一任务填充）**

```python
# src/email_mcp/tools/__init__.py
"""工具层：把服务层方法注册为 MCP 工具。"""
```

```python
# src/email_mcp/tools/read_tools.py
from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    """注册读取组工具。"""
```

```python
# src/email_mcp/tools/send_tools.py
from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    """注册发送/草稿组工具。"""
```

```python
# src/email_mcp/tools/action_tools.py
from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    """注册操作组工具。"""
```

```python
# src/email_mcp/tools/advanced_tools.py
from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    """注册高级组工具。"""
```

- [ ] **Step 5: 运行确认失败（工具未注册，断言 27 个会失败）**

运行：`uv run pytest tests/unit/test_server.py -v`
期望：FAIL，`assert {'list_inbox', ...} <= names`（当前只有 0 个工具）——这是预期的红，全部工具注册完（Task 18-21）后变绿。

- [ ] **Step 6: 提交（提交时测试仍红，属于任务依赖；Task 21 完成后全绿）**

```bash
git add src/email_mcp/context.py src/email_mcp/server.py src/email_mcp/tools/
git commit -m "feat: MCP 服务器入口与上下文容器（工具注册骨架）"
```

---

### Task 18: 读取组工具 read_tools.py

**Files:**
- Modify: `src/email_mcp/tools/read_tools.py`
- Test: `tests/unit/test_tools_read.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_tools_read.py
from email_mcp.context import AppContext
from email_mcp.server import build_server
from tests.unit.fakes import FakeProvider


def call_tool(mcp, name, **kwargs):
    return mcp.call_tool(name, arguments=kwargs)


def test_list_inbox_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "list_inbox", page=1, page_size=2)
    assert "s1" in str(result)


def test_read_email_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "read_email", email_id="INBOX:1")
    assert "s1" in str(result)


def test_read_email_missing_returns_structured_error(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "read_email", email_id="INBOX:999")
    assert "EMAIL_NOT_FOUND" in str(result)


def test_search_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "search_emails", query="s2")
    assert "s2" in str(result)
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_tools_read.py -v`
期望：FAIL，`Unknown tool: list_inbox`

- [ ] **Step 3: 写实现（替换占位）**

```python
# src/email_mcp/tools/read_tools.py
from __future__ import annotations

from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    svc = ctx.email_service
    thread = ctx.thread_service

    @mcp.tool(description="分页列出邮件，支持未读/发件人/文件夹过滤")
    def list_inbox(
        folder: str = "INBOX",
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        from_email: str | None = None,
    ) -> dict:
        return svc.list_inbox(
            page=page, page_size=page_size,
            unread_only=unread_only, from_email=from_email, folder=folder,
        )

    @mcp.tool(description="读取单封邮件完整内容（纯文本正文 + 附件元信息）")
    def read_email(email_id: str) -> dict:
        return svc.read_email(email_id)

    @mcp.tool(description="拉取整条会话线程")
    def get_thread(email_id: str) -> dict:
        return thread.get_thread(email_id)

    @mcp.tool(description="关键词/发件人/日期范围搜索")
    def search_emails(
        query: str = "",
        from_email: str | None = None,
        since: str | None = None,
        until: str | None = None,
        folder: str = "INBOX",
    ) -> dict:
        return svc.search_emails(
            query=query, from_email=from_email, since=since, until=until, folder=folder
        )

    @mcp.tool(description="列出所有文件夹")
    def list_folders() -> dict:
        return svc.list_folders()

    @mcp.tool(description="列出某邮件的附件元信息")
    def get_attachments(email_id: str) -> dict:
        return svc.get_attachments(email_id)

    @mcp.tool(description="按 part_id 下载附件，返回 base64 内容")
    def download_attachment(email_id: str, part_id: str) -> dict:
        return svc.download_attachment(email_id, part_id)

    @mcp.tool(description="读取原始 RFC 822 邮件头")
    def get_email_headers(email_id: str) -> dict:
        return svc.get_email_headers(email_id)

    @mcp.tool(description="返回当前账号身份信息")
    def get_account_info() -> dict:
        return svc.get_account_info()
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_tools_read.py -v`
期望：PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/tools/read_tools.py tests/unit/test_tools_read.py
git commit -m "feat: 读取组 9 个 MCP 工具"
```

---

### Task 19: 发送/草稿组工具 send_tools.py

**Files:**
- Modify: `src/email_mcp/tools/send_tools.py`
- Test: `tests/unit/test_tools_send.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_tools_send.py
from email_mcp.context import AppContext
from email_mcp.server import build_server


def call_tool(mcp, name, **kwargs):
    return mcp.call_tool(name, arguments=kwargs)


def test_send_email_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "send_email", to=["a@b.com"], subject="Hi", body="Hello")
    assert "sent-" in str(result)


def test_send_email_invalid_recipient(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "send_email", to=["bad"], subject="Hi", body="Hello")
    assert "INVALID_RECIPIENT" in str(result)


def test_save_draft_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "save_draft", to=["a@b.com"], subject="D", body="WIP")
    assert "Drafts:" in str(result)


def test_list_drafts_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    call_tool(mcp, "save_draft", to=["a@b.com"], subject="D", body="WIP")
    result = call_tool(mcp, "list_drafts")
    assert "D" in str(result)
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_tools_send.py -v`
期望：FAIL，`Unknown tool: send_email`

- [ ] **Step 3: 写实现**

```python
# src/email_mcp/tools/send_tools.py
from __future__ import annotations

from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    svc = ctx.email_service

    @mcp.tool(description="直接发送邮件（立即投递）")
    def send_email(
        to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict:
        return svc.send_email(to=to, cc=cc, subject=subject, body=body)

    @mcp.tool(description="存草稿到 Drafts 文件夹（人工确认后手动发送）")
    def save_draft(
        to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict:
        return svc.save_draft(to=to, cc=cc, subject=subject, body=body)

    @mcp.tool(description="列出草稿")
    def list_drafts() -> dict:
        return svc.list_drafts()
```

- [ ] **Step 4: 运行确认通过**

运行：`uv run pytest tests/unit/test_tools_send.py -v`
期望：PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add src/email_mcp/tools/send_tools.py tests/unit/test_tools_send.py
git commit -m "feat: 发送/草稿组 3 个 MCP 工具"
```

---

### Task 20: 操作组工具 action_tools.py

**Files:**
- Modify: `src/email_mcp/tools/action_tools.py`
- Modify: `src/email_mcp/service/email_service.py`（追加操作方法与引用块生成）
- Test: `tests/unit/test_email_service_actions.py`
- Test: `tests/unit/test_tools_action.py`

- [ ] **Step 1: 写失败测试（服务层操作 + 引用块）**

```python
# tests/unit/test_email_service_actions.py
from email_mcp.service.email_service import build_quote_block, EmailService


def test_build_quote_block():
    block = build_quote_block("Sender Name", "2026-01-01 10:00", "original body")
    assert "Sender Name" in block
    assert "original body" in block
    assert block.startswith("> ")


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_reply_email_prefills_and_quotes(account, provider):
    svc = make_service(account, provider)
    result = svc.reply_email("INBOX:1", body="Thanks!")
    assert result["success"] is True
    sent = provider.sent[0]
    assert sent["to"] == ["sender@x.com"]
    assert "Thanks!" in sent["body"]
    assert "> " in sent["body"]


def test_forward_email(account, provider):
    svc = make_service(account, provider)
    result = svc.forward_email("INBOX:1", to=["f@b.com"], body="FYI")
    assert result["success"] is True
    assert provider.sent[0]["to"] == ["f@b.com"]


def test_mark_read_unread(account, provider):
    svc = make_service(account, provider)
    svc.mark_read("INBOX:2")
    svc.mark_unread("INBOX:1")
    assert "\\Seen" in provider.get_message(account, "INBOX", "2").flags
    assert "\\Seen" not in provider.get_message(account, "INBOX", "1").flags


def test_archive_and_trash_are_soft(account, provider):
    svc = make_service(account, provider)
    svc.archive("INBOX:1")
    svc.trash("INBOX:2")
    assert provider.get_message(account, "All Mail", "1").folder == "All Mail"
    assert provider.get_message(account, "Trash", "2").folder == "Trash"
```

```python
# tests/unit/test_tools_action.py
from email_mcp.context import AppContext
from email_mcp.server import build_server


def call_tool(mcp, name, **kwargs):
    return mcp.call_tool(name, arguments=kwargs)


def test_reply_tool(account, provider):
    mcp = build_server(AppContext(account=account, provider=provider))
    result = call_tool(mcp, "reply_email", email_id="INBOX:1", body="Thanks!")
    assert "success" in str(result)
    assert provider.sent[0]["to"] == ["sender@x.com"]
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_email_service_actions.py tests/unit/test_tools_action.py -v`
期望：FAIL，`ImportError: cannot import name 'build_quote_block'`

- [ ] **Step 3: 追加服务层实现（email_service.py 末尾）**

```python
    # ---- 操作组 ----

    def reply_email(self, email_id: str, body: str, cc: list[str] | None = None) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            try:
                original = self.provider.get_message(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            quote = build_quote_block(
                original.from_.name or original.from_.email,
                original.date.strftime("%Y-%m-%d %H:%M"),
                original.body,
            )
            full_body = f"{body}\n\n{quote}"
            self._validate_recipients([original.from_.email], cc)
            message_id = self.provider.send(
                self.account, to=[original.from_.email], cc=cc,
                subject=f"Re: {original.subject}", body=full_body,
            )
            return {"message_id": message_id, "in_reply_to": original.id}
        return self._wrap(run)

    def forward_email(self, email_id: str, to: list[str], body: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            try:
                original = self.provider.get_message(self.account, folder, uid)
            except KeyError:
                raise EmailMCPError(ErrorCode.EMAIL_NOT_FOUND, f"未找到邮件 {email_id}") from None
            quote = build_quote_block(
                original.from_.name or original.from_.email,
                original.date.strftime("%Y-%m-%d %H:%M"),
                original.body,
            )
            full_body = f"{body}\n\n---------- 转发 ----------\n{quote}"
            self._validate_recipients(to)
            message_id = self.provider.send(
                self.account, to=to, cc=None,
                subject=f"Fwd: {original.subject}", body=full_body,
            )
            return {"message_id": message_id}
        return self._wrap(run)

    def mark_read(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            self.provider.mark_read(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def mark_unread(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            self.provider.mark_unread(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def archive(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            self.provider.archive(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def move_email(self, email_id: str, dest_folder: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            self.provider.move(self.account, folder, uid, dest_folder)
            return {"email_id": email_id, "dest_folder": dest_folder}
        return self._wrap(run)

    def trash_email(self, email_id: str) -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            self.provider.trash(self.account, folder, uid)
            return {"email_id": email_id}
        return self._wrap(run)

    def set_flag(self, email_id: str, flag: str = "\\Flagged") -> dict:
        def run():
            folder, uid = self._parse_email_id(email_id)
            self.provider.set_flag(self.account, folder, uid, flag)
            return {"email_id": email_id, "flag": flag}
        return self._wrap(run)

    def pin_email(self, email_id: str) -> dict:
        return self.set_flag(email_id, "\\Flagged")

    def snooze_email(self, email_id: str, until: str) -> dict:
        def run():
            if ctx_scheduler is None:
                raise EmailMCPError(ErrorCode.CONFIG_MISSING, "调度器未初始化")
            ctx_scheduler.add_snooze({"id": email_id, "until": until, "email_id": email_id})
            return {"email_id": email_id, "snoozed_until": until}
        return self._wrap(run)
```

说明：`snooze_email` 依赖 `ctx.scheduler_store`，需要把 store 传入 EmailService。在 `context.py` 的 `__post_init__` 中注入：

```python
    def __post_init__(self) -> None:
        self.scheduler_store = SchedulerStore(Path("data/scheduler.json"))
        self.email_service = EmailService(self.provider, self.account, self.scheduler_store)
        self.thread_service = ThreadService(self.provider, self.account)
        self.unsubscribe_service = UnsubscribeService(self.provider, self.account)
```

并在 `EmailService.__init__` 增加可选参数与模块级 `build_quote_block`：

```python
# 修改 EmailService.__init__ 签名
    def __init__(self, provider, account, scheduler_store=None):
        self.provider = provider
        self.account = account
        self.scheduler_store = scheduler_store
```

在文件顶部（import 之后）加引用块生成函数：

```python
def build_quote_block(sender: str, date_str: str, original_body: str) -> str:
    """生成 'On ... wrote:' 风格引用块。"""
    lines = []
    for line in (original_body or "").splitlines():
        lines.append(f"> {line}")
    header = f"On {date_str} {sender} wrote:"
    return header + "\n" + "\n".join(lines)
```

`snooze_email` 里的 `ctx_scheduler` 改为 `self.scheduler_store`：

```python
    def snooze_email(self, email_id: str, until: str) -> dict:
        def run():
            if self.scheduler_store is None:
                raise EmailMCPError(ErrorCode.CONFIG_MISSING, "调度器未初始化")
            self.scheduler_store.add_snooze(
                {"id": email_id, "until": until, "email_id": email_id}
            )
            return {"email_id": email_id, "snoozed_until": until}
        return self._wrap(run)
```

- [ ] **Step 4: 写工具层实现（action_tools.py）**

```python
# src/email_mcp/tools/action_tools.py
from __future__ import annotations

from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    svc = ctx.email_service

    @mcp.tool(description="回复邮件：自动生成引用块并填收件人")
    def reply_email(email_id: str, body: str, cc: list[str] | None = None) -> dict:
        return svc.reply_email(email_id, body, cc)

    @mcp.tool(description="转发邮件：自动生成引用块")
    def forward_email(email_id: str, to: list[str], body: str) -> dict:
        return svc.forward_email(email_id, to, body)

    @mcp.tool(description="标记已读")
    def mark_read(email_id: str) -> dict:
        return svc.mark_read(email_id)

    @mcp.tool(description="标记未读")
    def mark_unread(email_id: str) -> dict:
        return svc.mark_unread(email_id)

    @mcp.tool(description="归档（移入 All Mail）")
    def archive(email_id: str) -> dict:
        return svc.archive(email_id)

    @mcp.tool(description="移动到指定文件夹")
    def move_email(email_id: str, dest_folder: str) -> dict:
        return svc.move_email(email_id, dest_folder)

    @mcp.tool(description="移入废纸篓（软删除）")
    def trash_email(email_id: str) -> dict:
        return svc.trash_email(email_id)

    @mcp.tool(description="设置邮件标记（默认星标 \\Flagged）")
    def set_flag(email_id: str, flag: str = "\\Flagged") -> dict:
        return svc.set_flag(email_id, flag)

    @mcp.tool(description="置顶/星标邮件")
    def pin_email(email_id: str) -> dict:
        return svc.pin_email(email_id)

    @mcp.tool(description="延后提醒（until 为 ISO 时间，到期重新标记未读）")
    def snooze_email(email_id: str, until: str) -> dict:
        return svc.snooze_email(email_id, until)
```

- [ ] **Step 5: 运行确认通过**

运行：`uv run pytest tests/unit/test_email_service_actions.py tests/unit/test_tools_action.py -v`
期望：PASS（7 passed）

- [ ] **Step 6: 提交**

```bash
git add src/email_mcp/service/email_service.py src/email_mcp/context.py src/email_mcp/tools/action_tools.py tests/unit/test_email_service_actions.py tests/unit/test_tools_action.py
git commit -m "feat: 操作组 10 个 MCP 工具（回复/转发/标记/归档/星标/snooze）"
```

---

### Task 21: 高级组工具 advanced_tools.py

**Files:**
- Modify: `src/email_mcp/tools/advanced_tools.py`
- Modify: `src/email_mcp/service/email_service.py`（追加 batch_send / schedule_send / 标签操作）
- Test: `tests/unit/test_email_service_advanced.py`
- Test: `tests/unit/test_tools_advanced.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_email_service_advanced.py
import pytest
from email_mcp.errors import ErrorCode
from email_mcp.service.email_service import EmailService
from email_mcp.service.guardrails import BATCH_SIZE_LIMIT


def make_service(account, provider) -> EmailService:
    return EmailService(provider=provider, account=account)


def test_batch_send_ok(account, provider):
    svc = make_service(account, provider)
    result = svc.batch_send(to=["a@b.com", "c@d.com"], subject="Hi", body="Hello")
    assert result["success"] is True
    assert len(provider.sent) == 2


def test_batch_send_over_limit(account, provider):
    svc = make_service(account, provider)
    result = svc.batch_send(
        to=[f"u{i}@x.com" for i in range(BATCH_SIZE_LIMIT + 1)],
        subject="Hi", body="Hello",
    )
    assert result["success"] is False
    assert result["error"]["code"] == "BATCH_LIMIT_EXCEEDED"
    assert provider.sent == []


def test_schedule_send_stores_item(account, provider, tmp_path):
    from email_mcp.service.scheduler import SchedulerStore
    store = SchedulerStore(tmp_path / "sched.json")
    svc = EmailService(provider=provider, account=account, scheduler_store=store)
    result = svc.schedule_send(
        to=["a@b.com"], subject="Later", body="Hi",
        send_at="2099-01-01T09:00:00+00:00",
    )
    assert result["success"] is True
    assert store.load()["scheduled_sends"][0]["subject"] == "Later"


def test_create_label_creates_folder(account, provider):
    svc = make_service(account, provider)
    assert svc.create_label("Work")["success"] is True
    assert "Work" in provider.list_folders(account)
```

- [ ] **Step 2: 运行确认失败**

运行：`uv run pytest tests/unit/test_email_service_advanced.py -v`
期望：FAIL，`AttributeError: 'EmailService' object has no attribute 'batch_send'`

- [ ] **Step 3: 追加服务层实现（email_service.py 末尾）**

```python
    # ---- 高级组 ----

    def batch_send(self, to: list[str], subject: str, body: str) -> dict:
        def run():
            from email_mcp.service.guardrails import check_batch_size

            check_batch_size(to)
            self._validate_recipients(to)
            message_ids = []
            for addr in to:
                mid = self.provider.send(
                    self.account, to=[addr], cc=None, subject=subject, body=body
                )
                message_ids.append(mid)
            return {"sent": len(message_ids), "message_ids": message_ids}
        return self._wrap(run)

    def schedule_send(
        self, to: list[str], subject: str, body: str, send_at: str
    ) -> dict:
        def run():
            if self.scheduler_store is None:
                raise EmailMCPError(ErrorCode.CONFIG_MISSING, "调度器未初始化")
            self._validate_recipients(to)
            from uuid import uuid4

            item = {
                "id": str(uuid4()),
                "to": to,
                "subject": subject,
                "body": body,
                "send_at": send_at,
            }
            self.scheduler_store.add_scheduled_send(item)
            return {"schedule_id": item["id"], "send_at": send_at}
        return self._wrap(run)

    def create_label(self, name: str) -> dict:
        def run():
            self.provider.create_folder(self.account, name)
            return {"label": name}
        return self._wrap(run)

    def manage_labels(self, action: str, name: str | None = None) -> dict:
        def run():
            if action == "list":
                return {"labels": self.provider.list_folders(self.account)}
            if action == "delete" and name:
                self.provider.delete_folder(self.account, name)
                return {"deleted": name}
            raise EmailMCPError(
                ErrorCode.CONFIG_INVALID,
                "action 只能是 list 或 delete（delete 需提供 name）",
            )
        return self._wrap(run)
```

说明：`create_label`/`manage_labels` 需要 Provider 支持 `create_folder`/`delete_folder`。给 Protocol 与 FakeProvider、ImapProvider 补充（Task 4/5/16 的文件各加两个方法）：

```python
# base.py 追加
    def create_folder(self, account: Account, name: str) -> None: ...
    def delete_folder(self, account: Account, name: str) -> None: ...
```

```python
# fakes.py 追加
    def create_folder(self, account, name):
        if name not in self.messages and name not in self._folders:
            self._folders.append(name)

    def delete_folder(self, account, name):
        self._folders = [f for f in self._folders if f != name]
```

并把 `FakeProvider.list_folders` 改为基于 `self._folders`（初始化 `["INBOX", "Sent"]`）：

```python
    def __init__(self, messages=None):
        self.messages: list[EmailMessage] = messages or []
        self.sent: list[dict] = []
        self.drafts: list[EmailMessage] = []
        self._folders: list[str] = ["INBOX", "Sent"]

    def list_folders(self, account):
        return sorted(self._folders)
```

```python
# imap_provider.py 追加
    def create_folder(self, account, name):
        with self._imap(account).connect() as conn:
            status, _ = conn.create(name)
            if status != "OK":
                raise EmailMCPError(ErrorCode.INTERNAL, f"创建文件夹失败: {name}")

    def delete_folder(self, account, name):
        with self._imap(account).connect() as conn:
            status, _ = conn.delete(name)
            if status != "OK":
                raise EmailMCPError(ErrorCode.INTERNAL, f"删除文件夹失败: {name}")
```

- [ ] **Step 4: 写工具层实现（advanced_tools.py）**

```python
# src/email_mcp/tools/advanced_tools.py
from __future__ import annotations

from email_mcp.context import AppContext


def register(mcp, ctx: AppContext) -> None:
    svc = ctx.email_service

    @mcp.tool(description="基于 List-Unsubscribe 头自动退订")
    def unsubscribe(email_id: str) -> dict:
        return ctx.unsubscribe_service.unsubscribe(email_id)

    @mcp.tool(description="定时发送（send_at 为 ISO 时间，服务器进程存活期间到期执行）")
    def schedule_send(
        to: list[str], subject: str, body: str, send_at: str
    ) -> dict:
        return svc.schedule_send(to=to, subject=subject, body=body, send_at=send_at)

    @mcp.tool(description=f"同模板批量发送（每批最多 20 封）")
    def batch_send(to: list[str], subject: str, body: str) -> dict:
        return svc.batch_send(to=to, subject=subject, body=body)

    @mcp.tool(description="创建标签（IMAP 映射为文件夹）")
    def create_label(name: str) -> dict:
        return svc.create_label(name)

    @mcp.tool(description="标签管理：action=list 列出，action=delete 删除（需 name）")
    def manage_labels(action: str, name: str | None = None) -> dict:
        return svc.manage_labels(action=action, name=name)
```

- [ ] **Step 5: 运行确认通过**

运行：`uv run pytest tests/unit/test_email_service_advanced.py tests/unit/test_tools_advanced.py -v`
期望：PASS

再跑全量：`uv run pytest`
期望：全部通过（含 Task 17 的 27 工具注册断言）

- [ ] **Step 6: 提交**

```bash
git add src/email_mcp/service/email_service.py src/email_mcp/tools/advanced_tools.py src/email_mcp/provider/base.py src/email_mcp/provider/imap_provider.py tests/unit/fakes.py tests/unit/test_email_service_advanced.py tests/unit/test_tools_advanced.py
git commit -m "feat: 高级组 5 个 MCP 工具（退订/定时/批量/标签）+ 27 工具全部注册"
```

---

## Phase 7：收尾与端到端验证

### Task 22: 质量检查与全量测试

**Files:**
- Modify: 无（仅运行命令）

- [ ] **Step 1: 运行 ruff**

运行：`uv run ruff check src tests`
期望：`All checks passed!`（如报错则修复格式问题）

- [ ] **Step 2: 运行 mypy**

运行：`uv run mypy src`
期望：`Success: no issues found`（如报错则修复类型标注，注意 `EmailProvider` 为 Protocol，实现类无需显式继承）

- [ ] **Step 3: 全量测试 + 覆盖率**

运行：`uv run pytest --cov=email_mcp --cov-report=term-missing`
期望：全部通过；服务层与工具层覆盖率 ≥ 90%（对未覆盖分支补测试）

- [ ] **Step 4: 提交（如有修复）**

```bash
git add -A
git commit -m "chore: 通过 ruff/mypy，全量测试覆盖达标"
```

---

### Task 23: README 完善与端到端验证清单

**Files:**
- Modify: `README.md`
- Modify: `.env.example`（如有遗漏）

- [ ] **Step 1: 在 README 增加 MCP 客户端配置示例**

```markdown
## Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "email": {
      "command": "uv",
      "args": ["run", "email-mcp"],
      "env": {
        "EMAIL_IMAP_HOST": "imap.example.com",
        "EMAIL_IMAP_PORT": "993",
        "EMAIL_SMTP_HOST": "smtp.example.com",
        "EMAIL_SMTP_PORT": "465",
        "EMAIL_USERNAME": "you@example.com",
        "EMAIL_AUTH_MODE": "app_password",
        "EMAIL_AUTH_SECRET": "your-app-password"
      }
    }
  }
}
```

## 端到端手动验证清单（需真实测试邮箱）

1. `cp .env.example .env` 并填入测试邮箱的 IMAP/SMTP 配置
2. `uv run email-mcp` 启动 stdio 服务器
3. 用 MCP Inspector 或 Claude Desktop 连接，依次验证：
   - [ ] `list_inbox` 返回测试邮箱收件箱
   - [ ] `read_email` 能读取一封邮件正文
   - [ ] `save_draft` 在网页邮箱的草稿箱出现草稿
   - [ ] 在网页邮箱手动发送该草稿（人工确认路径）
   - [ ] `send_email` 发送后收件人收到、Sent 文件夹有记录
   - [ ] `search_emails` 按关键词命中
   - [ ] `mark_read` / `mark_unread` 状态变化在网页可见
   - [ ] `batch_send` 超过 20 封时返回 BATCH_LIMIT_EXCEEDED
4. `uv run email-mcp --http` 启动 HTTP 模式，配置 `EMAIL_HTTP_TOKEN` 后用 Bearer token 连接验证
```

- [ ] **Step 2: 运行文档中的命令核对**

运行：`uv run email-mcp --help`
期望：显示 `--http` 参数说明，无报错。

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: README 客户端配置与端到端验证清单"
```

---

## 自检记录

**1. 规格覆盖：**
- 27 个工具：Task 18（读取 9）、Task 19（发送/草稿 3）、Task 20（操作 10）、Task 21（高级 5）✓
- 五层架构：Task 2/3（模型/错误）、Task 4-5（Provider 抽象）、Task 6-12（服务层）、Task 13（配置）、Task 14-16（IMAP/SMTP）、Task 17-21（MCP 层）✓
- stdio + HTTP 双入口：Task 17 `main()` ✓
- 双认证模式：Task 13 `auth_mode` ✓
- 多账号预留：`Account.account_id` + `EmailMessage.account_id` 字段 ✓
- 草稿即确认：Task 8 `save_draft` + Task 19 工具 + README 人工确认路径 ✓
- 安全：Task 12（护栏/脱敏）、Task 16 软删、Task 3 错误脱敏约定 ✓
- 三层测试：单元（Task 6-12）、集成 mock（Task 14-16）、E2E 手动（Task 23）✓

**2. 占位符扫描：** 无 TBD/TODO；每个代码步骤均有完整代码。

**3. 类型一致性：**
- `EmailService(provider, account, scheduler_store=None)` 签名在 Task 8 引入，Task 20/21 复用时保持。
- `ThreadService(provider, account)` 在 Task 9 修正后，Task 17 `context.py` 构造保持一致。
- `EmailProvider` 的 `create_folder`/`delete_folder` 在 Task 21 补充后，FakeProvider 与 ImapProvider 同步实现。
- 错误码 `UNSUBSCRIBE_UNSUPPORTED` 在 Task 10 补充到 errors.py，后续任务引用一致。
