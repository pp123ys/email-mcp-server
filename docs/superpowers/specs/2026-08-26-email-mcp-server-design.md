# 邮件 MCP 服务器设计文档

- 日期：2026-08-26
- 状态：已批准（分节确认）
- 项目目录：`D:\text\email service`

## 1. 项目概述

构建一个 **邮件 MCP 服务器（MCP server）**，通过 MCP 协议为外部 agent 提供"连接邮件"的手段——读取收件箱、阅读邮件内容、发送邮件等完整邮件操作能力。

**范围边界（关键）**：本项目的职责**仅限于**把邮件能力干净地暴露给外部 agent。所有智能逻辑——邮件分类、回复起草、审校、多代理编排、风险判断——全部由外部 agent（Claude Desktop、Cursor、自研 agent 等）负责。本项目**不实现**任何智能编排逻辑，也不提供审批 UI。

### 决策汇总

| 决策点 | 结论 |
|---|---|
| 项目范围 | 仅邮件 MCP 服务器；智能逻辑由外部 agent 负责 |
| 技术栈 | Python（官方 MCP SDK） |
| 传输方式 | stdio + HTTP（Streamable HTTP）双入口，核心与传输解耦 |
| 邮件接入 | 通用 IMAP/SMTP（第一版），预留 Gmail/Outlook 适配层 |
| 工具集 | 全部 27 个工具进第一版 |
| 凭据存储 | 环境变量 / `.env` |
| 认证方式 | 应用专用密码 + 主密码都支持，配置二选一 |
| 多账号 | 第一版单账号；数据模型与配置结构按多账号设计 |
| 人工确认 | 草稿即确认：`save_draft` 存 IMAP Drafts，客户端审核后手动发送 |

## 2. 整体架构

```
┌──────────────────────────────────────────────┐
│          MCP 客户端（外部 agent）              │
│   Claude Desktop / Cursor / 自研 agent       │
└───────────────────┬──────────────────────────┘
                    │ MCP 协议 (JSON-RPC 2.0)
┌───────────────────┴──────────────────────────┐
│            传输层 (双入口)                    │
│  StdioTransport  │  Streamable HTTP           │
└───────────────────┬──────────────────────────┘
┌───────────────────┴──────────────────────────┐
│          MCP Server (FastMCP)                │
│  27 工具注册、参数校验、类型转换              │
└───────────────────┬──────────────────────────┘
┌───────────────────┴──────────────────────────┐
│          服务层 EmailService                 │
│  分页/过滤、引用块生成、退订解析、线程聚合     │
└───────────────────┬──────────────────────────┘
┌───────────────────┴──────────────────────────┐
│       Provider 层（抽象层）                   │
│  EmailProvider (Protocol)                    │
│   ├─ ImapProvider    ← 第一版 (imaplib+smtplib)│
│   └─ (预留) GmailProvider / OutlookProvider   │
└───────────────────┬──────────────────────────┘
┌───────────────────┴──────────────────────────┐
│          配置层 Config                        │
│  .env → 环境变量 → Account 模型              │
└──────────────────────────────────────────────┘
```

### 五层职责

1. **传输层**：使用官方 MCP Python SDK 的 `FastMCP`，同一套代码支持 `stdio` 和 `http`（Streamable HTTP）两种传输——通过 `transport` 参数切换，不写两套服务器。
2. **MCP Server 层**：注册 21 个工具，做参数校验和类型转换，不触碰任何邮件逻辑。
3. **服务层 `EmailService`**：纯业务逻辑，不依赖 IMAP 细节——分页计算、未读/发件人过滤、引用块生成（"On... wrote:"）、`List-Unsubscribe` 头解析、线程聚合。本层可脱离真实邮箱做单元测试。
4. **Provider 层**：`EmailProvider` 抽象接口 + `ImapProvider` 实现。服务层只依赖接口；未来接 Gmail/Outlook 仅需新增实现文件并注册，不动上三层。
5. **配置层**：启动时从环境变量构建 `Account` 模型（v1 单账号；模型字段按多账号设计，未来配置数组即可扩展）。

**关键决策**：工具层 → 服务层 → Provider 层，依赖方向单向向下；每一层都可独立测试和替换。

## 3. 数据模型（Pydantic）

```
EmailMessage          # 一封邮件的完整表示
├─ id            str        # 全局唯一消息 ID（IMAP UID + folder 组合）
├─ account_id    str        # 所属账号（预留多账号）
├─ folder        str        # 所在文件夹（INBOX / Drafts / Sent…）
├─ subject       str
├─ from_         EmailAddress
├─ to            list[EmailAddress]
├─ cc            list[EmailAddress]
├─ date          datetime    # 发送时间
├─ flags         list[str]   # 已读/未读/星标
├─ body          str         # 纯文本正文（自动剥离 HTML 标签）
├─ body_html     str | None  # 原始 HTML 正文
├─ attachments   list[AttachmentMeta]   # 附件元信息
├─ message_id    str         # RFC 822 Message-ID（线程关联用）
├─ in_reply_to   str | None  # 回复链关联
└─ headers       dict[str, str]  # 原始头（get_email_headers 用）

EmailAddress
├─ name    str | None
└─ email   str

AttachmentMeta     # 附件元信息（内容不加载进内存）
├─ filename   str
├─ size       int
├─ mime_type  str
└─ part_id    str    # 供 download_attachment 定位

Account           # v1 单实例；字段已多账号化
├─ account_id      str
├─ imap_host / imap_port / imap_ssl  bool
├─ smtp_host / smtp_port / smtp_ssl  bool
├─ username        str
├─ auth_mode       "app_password" | "password"   # 二选一
├─ auth_secret     str            # 环境变量读取，绝不落盘日志
└─ sent_folder     str            # 发送后归档文件夹（Sent）
```

### 关键设计点

1. **邮件 ID 用 `folder + UID` 组合**：IMAP 的 UID 只在同一文件夹内唯一，跨文件夹必须带上 folder，否则 `get_thread`/`read_email` 会拿错邮件。
2. **正文双轨**：`body` 自动剥离 HTML 保留纯文本（节省 agent token），`body_html` 单独保留供按需取用。
3. **附件只存元信息**：内容不加载进内存；`download_attachment` 才真正拉取，避免大附件撑爆上下文。
4. **`Account.auth_secret` 只从环境变量注入**：日志、错误信息、工具返回全部脱敏。

## 4. 工具清单（27 个，全部进第一版）

> 注：`mark_read`/`mark_unread`、`set_flag`/`pin_email`、`create_label`/`manage_labels` 为成对工具，各占一个表格行、算两个工具名。此前讨论中提过的 `get_inbox_stats`、`list_contacts` 不在第一版范围内（按需后续追加）。

### 读取组（9）

| 工具 | 说明 |
|---|---|
| `list_inbox` | 分页列出收件箱，支持未读/发件人/文件夹过滤 |
| `read_email` | 读单封邮件完整内容（纯文本正文 + 附件元信息） |
| `get_thread` | 拉取整条会话线程（Message-ID 关联的所有邮件） |
| `search_emails` | 关键词/发件人/日期范围搜索 |
| `list_folders` | 列出所有文件夹 |
| `get_attachments` | 列出某邮件的附件元信息 |
| `download_attachment` | 按 part_id 下载附件内容 |
| `get_email_headers` | 读取原始 RFC 822 头 |
| `get_account_info` | 返回当前账号身份信息 |

### 草稿/待发组（3）

| 工具 | 说明 |
|---|---|
| `save_draft` | 存草稿到 IMAP Drafts 文件夹 |
| `list_drafts` | 列出草稿 |
| `send_email` | 直接发送（立即投递） |

### 操作组（8）

| 工具 | 说明 |
|---|---|
| `reply_email` | 回复：自动生成引用块 + 自动填收件人 |
| `forward_email` | 转发：自动生成引用块 |
| `mark_read` / `mark_unread` | 标记已读/未读 |
| `archive` | 归档（移入 All Mail 或归档文件夹） |
| `move_email` | 移动到指定文件夹 |
| `trash_email` | 移入废纸篓（软删） |
| `set_flag` / `pin_email` | 星标/置顶 |
| `snooze_email` | 延后（写本地状态，到期重新标记） |

### 高级组（4）

| 工具 | 说明 |
|---|---|
| `unsubscribe` | 解析 `List-Unsubscribe` 头自动退订 |
| `schedule_send` | 定时发送（本地队列 + 定时器） |
| `batch_send` | 同模板批量发送（节流 + 收件人校验） |
| `create_label` / `manage_labels` | 标签管理（IMAP 映射为文件夹/关键字） |

## 5. 数据流：人工确认的双路径

```
路径 A（直接发送）         路径 B（人工确认 - 草稿即确认）
┌──────────────┐          ┌──────────────────┐
│ agent 调      │          │ agent 调          │
│ send_email    │          │ save_draft        │
└──────┬───────┘          └────────┬─────────┘
       ▼                          ▼
┌──────────────┐          ┌──────────────────┐
│ SMTP 发送    │          │ IMAP Drafts 存草稿│ ← 用户在任意邮件
└──────┬───────┘          └────────┬─────────┘   客户端审核草稿
       ▼                          ▼
┌──────────────┐          ┌──────────────────┐
│ 移入 Sent     │          │ 用户手动点击发送  │
│ 文件夹        │          └──────────────────┘
└──────────────┘
```

**人工确认落地方式（已确认：方式 1）**：`save_draft` 将草稿存入 IMAP Drafts 文件夹，用户在任意邮件客户端（网页/App）审核草稿并手动发送。服务器不介入发送环节。这与"只要 MCP 连接手段"的项目边界一致。

## 6. 错误处理

所有工具统一返回结构化错误：

```json
{
  "success": false,
  "error": {
    "code": "IMAP_AUTH_FAILED",
    "message": "认证失败，请检查账号密码或授权码",
    "details": {}
  }
}
```

### 错误码体系

| 类别 | 错误码示例 |
|---|---|
| 配置错误 | `CONFIG_MISSING`、`CONFIG_INVALID`、`AUTH_UNSUPPORTED` |
| 认证错误 | `IMAP_AUTH_FAILED`、`SMTP_AUTH_FAILED`、`TOKEN_EXPIRED`（预留 OAuth） |
| 连接错误 | `IMAP_CONNECT_FAILED`、`SMTP_CONNECT_FAILED`、`CONNECTION_TIMEOUT` |
| 操作错误 | `EMAIL_NOT_FOUND`、`FOLDER_NOT_FOUND`、`ATTACHMENT_NOT_FOUND`、`INVALID_RECIPIENT`、`EMAIL_TOO_LARGE` |
| 限流错误 | `RATE_LIMITED`、`BATCH_LIMIT_EXCEEDED` |

**重试与超时**：IMAP/SMTP 连接默认超时 15s；瞬时网络错误自动重试 2 次（指数退避）；超过返回 `CONNECTION_TIMEOUT`。

## 7. 安全设计

1. **凭据零泄露**：`auth_secret` 只从环境变量读取；日志、错误信息、工具返回值全部脱敏（`***`）。异常信息返回前统一过脱敏器。
2. **发送护栏（服务器侧，不依赖 agent 自觉）**：
   - 收件人格式校验（`email-validator`），非法地址直接拒绝
   - `batch_send` 每批上限 20 封、间隔节流，防触发邮箱反垃圾风控
   - 单账号发送频率上限（可配置）
3. **TLS 强制**：IMAP/SMTP 一律走 SSL/STARTTLS，禁止明文连接（可配置关闭，仅限调试）。
4. **附件安全**：`download_attachment` 返回内容前检查大小上限（默认 25MB）；可选开启 MIME 类型白名单校验。
5. **软删除**：`trash_email` 只移入废纸篓，绝不物理删除。
6. **`.env` 治理**：`.env` 加入 `.gitignore`；提供 `.env.example` 模板；README 明确提示不提交凭据。
7. **HTTP 传输安全**：Streamable HTTP 支持 Bearer token 认证——配置 token 则要求请求带 `Authorization` 头；未配置则只监听 localhost。

> **已接受的实现偏差（2026-08-27 记录）**：锁定的 mcp 1.29.x 的 `FastMCP.run()` 不提供静态 Bearer 认证参数（仅 OAuth 钩子）。因此 `EMAIL_HTTP_TOKEN` 当前不校验请求，仅在 `--http` 启动时产生警告。缓解措施：默认仅绑定 `127.0.0.1` + README 明确说明 + 启动警告。若未来升级到支持静态认证的 mcp 版本，再启用 token 校验。

## 8. 测试策略

### 三层测试（不依赖真实邮箱）

1. **单元测试（pytest）**：服务层 + 工具层，用 `FakeProvider`（内存版 `EmailProvider` 实现）测试分页、过滤、引用块生成、退订解析、线程聚合等纯逻辑。目标覆盖率 ≥ 90%。
2. **集成测试**：用 mock（`imaplib`/`smtplib` 桩）验证协议调用序列正确（SELECT → FETCH → STORE 等）；验证 `.env` 加载、配置解析、错误码映射。
3. **端到端（可选，手动）**：连测试邮箱跑通 `list_inbox → read_email → save_draft` 全流程，验证真实 IMAP 兼容性。

## 9. 项目结构（Python + uv）

```
email-mcp-server/
├── pyproject.toml          # uv 管理依赖
├── .env.example            # 配置模板（不提交真实凭据）
├── .gitignore              # 含 .env
├── README.md
├── src/
│   └── email_mcp/
│       ├── __init__.py
│       ├── config.py       # 配置层：.env → Account 模型
│       ├── server.py       # MCP 服务器入口（stdio/http 切换）
│       ├── tools/          # 工具层
│       │   ├── read_tools.py
│       │   ├── send_tools.py
│       │   ├── action_tools.py
│       │   └── advanced_tools.py
│       ├── service/        # 服务层
│       │   ├── email_service.py
│       │   ├── thread_service.py
│       │   ├── unsubscribe_service.py
│       │   └── pagination.py
│       ├── provider/       # 抽象层
│       │   ├── base.py     # EmailProvider Protocol
│       │   ├── imap_provider.py
│       │   ├── imap_client.py    # IMAP 连接管理
│       │   └── smtp_client.py    # SMTP 发送
│       ├── models.py       # Pydantic 模型
│       └── errors.py       # 错误码 + 结构化错误
└── tests/
    ├── unit/               # FakeProvider 单测
    ├── integration/        # mock 集成测试
    └── conftest.py
```

### 依赖清单

- 运行时：`mcp`（官方 SDK，含 FastMCP + stdio/http 传输）、`pydantic`、`python-dotenv`、`email-validator`、`python-dateutil`
- 开发：`pytest`、`pytest-asyncio`、`ruff`、`mypy`

### 运行方式

```bash
uv run email-mcp            # 默认 stdio（Claude Desktop / Cursor 用）
uv run email-mcp --http     # HTTP 模式（Streamable HTTP）
```

## 10. 成功标准

1. 一个支持 MCP 的 agent 能通过本服务器完成：列出收件箱 → 阅读邮件 → 撰写草稿存草稿箱 → 审核后手动发送（人工确认路径）。
2. 27 个工具全部实现并通过单元/集成测试；服务层与工具层覆盖率 ≥ 90%。
3. 凭据在任何日志、错误信息、工具返回值中均不出现明文。
4. stdio 与 HTTP 两种传输方式均可正常运行。
5. 新增 Gmail/Outlook 提供者不需要修改工具层、服务层与配置层核心逻辑（仅新增 Provider 实现 + 注册）。
