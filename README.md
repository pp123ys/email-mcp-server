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

### 无凭据启动（agent 引导配置）

服务**不需要预置凭据也能启动**（stdio 与 HTTP 模式均可）：

```bash
uv run email-mcp            # 未配置 .env 也能启动，会提示"未配置邮箱"
```

未配置时，连接到服务的 agent 调用邮箱工具会收到 `CONFIG_MISSING` 引导错误，agent 应：

1. 调用 `get_account_status` 查看缺失配置项
2. 向用户询问邮箱凭据（IMAP/SMTP 主机、用户名、授权码）
3. 调用 `configure_account` 写入配置（凭据为敏感信息，写入前请先征得用户同意；写入后立即生效并持久化到 `.env`，重启自动加载）
4. 调用 `test_email_connection` 验证 IMAP/SMTP 登录是否成功

> 提示：`configure_account` 写入的 `.env` 已被 gitignore，不会进入版本库。

## 零基础快速上手（Windows 新手版）

第一次接触命令行？按下面一步步来即可，全程只需装一个工具。

### 1. 安装 uv

uv 是 Python 的包管理器，会自动帮你下载 Python 并安装项目依赖，**不用手动装 Python**。

1. 按 `Win` 键搜索 **PowerShell** 并打开，粘贴以下命令回车：
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. 装完后**关闭并重新打开** PowerShell，输入 `uv --version` 能看到版本号即成功。
3. Git 无需再装：用 `git clone` 克隆的已有 Git；从 GitHub 下载 ZIP 解压的也不需要。

### 2. 进入项目文件夹

```powershell
cd "D:\text\email service"
```

> 路径含空格必须加引号。也可以在资源管理器里进入该文件夹后，在地址栏输入 `powershell` 回车，即可在该目录打开 PowerShell。

### 3. 配置邮箱

```powershell
copy .env.example .env
```

用记事本打开 `.env`（右键 → 打开方式 → 记事本）并填写：

| 配置项 | 说明 |
| --- | --- |
| `EMAIL_IMAP_HOST` / `EMAIL_IMAP_PORT` | 收件服务器，如 QQ：`imap.qq.com` / `993`；163：`imap.163.com` / `993` |
| `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORT` | 发件服务器，如 QQ：`smtp.qq.com` / `465` |
| `EMAIL_USERNAME` | 你的邮箱地址 |
| `EMAIL_AUTH_SECRET` | **授权码，不是邮箱登录密码** |

授权码获取：登录邮箱网页版 → 设置/安全 → 开启 **IMAP/SMTP 服务** → 生成授权码（QQ / 163 走此流程；Gmail 为「应用专用密码」）。

### 4. 启动

```powershell
uv run email-mcp
```

首次运行会自动下载 Python 与依赖，需等待几分钟。看到启动提示即成功。若尚未配好邮箱，服务也能以「未配置邮箱」状态启动（见上文「无凭据启动」）。

### 5. 如何真正使用

该服务是 MCP 服务器，没有独立界面，需配合 MCP 客户端使用：

- 快速验证：`uv run email-mcp --http` 启动 HTTP 模式，用 [MCP Inspector](https://mcp.inspector.dev) 连接；
- 日常使用：按下方「Claude Desktop 配置」接入 Claude Desktop 或 Cursor（建议 args 使用 `--project "D:\text\email service"` 指向项目绝对路径）。

### 常见问题

- **`z-mail-agent-temp/` 是什么？** 与本项目无关的另一个示例（z-mail-agent），可忽略。
- **连接失败？** 确认邮箱网页版已开通 IMAP/SMTP 服务，且填的是授权码而非登录密码。
- **提示「uv 不是内部或外部命令」？** 重新打开 PowerShell 后再试，或重新执行第 1 步的安装命令。

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

> 提示：`uv run email-mcp` 需在项目根目录（含 pyproject.toml/uv.lock）执行；若 Claude Desktop 的工作目录不是项目根，可把 args 改为 `["run", "--project", "<项目绝对路径>", "email-mcp"]`。

## 端到端手动验证清单（需真实测试邮箱）

1. `cp .env.example .env` 并填入测试邮箱的 IMAP/SMTP 配置
2. `uv run email-mcp` 启动 stdio 服务器
3. 用 MCP Inspector 或 Claude Desktop 连接，依次验证：
   - [ ] `list_inbox` 返回测试邮箱收件箱
   - [ ] `read_email` 能读取一封邮件正文
   - [ ] `save_draft` 在网页邮箱的草稿箱出现草稿
   - [ ] 在网页邮箱手动发送该草稿（人工确认路径）
   - [ ] `send_email` 发送后收件人收到；Sent 文件夹有记录（多数服务商 SMTP 自动存件；若无记录属服务商设置，非本工具行为）
   - [ ] `search_emails` 按关键词命中
   - [ ] `mark_read` / `mark_unread` 状态变化在网页可见
   - [ ] `batch_send` 超过 20 封时返回 BATCH_LIMIT_EXCEEDED
4. `uv run email-mcp --http` 启动 HTTP 模式（Streamable HTTP，仅绑定 127.0.0.1），用 MCP 客户端经 HTTP 连接验证

> 注：当前 mcp 版本（1.29.x）不支持静态 Bearer 认证；`EMAIL_HTTP_TOKEN` 仅产生警告，不会校验请求。HTTP 模式应只在本机或可信反向代理后暴露。

> 注：Gmail 的已发送文件夹名为 `[Gmail]/Sent Mail`，可在 .env 中把 `EMAIL_SENT_FOLDER` 设为实际名称。

## 安全
- 凭据只从环境变量读取，日志/错误信息全部脱敏
- 批量发送限 20 封/批，发送频率可配置
- 删除一律软删（移入废纸篓）

## 测试
`uv run pytest` / `uv run ruff check .` / `uv run mypy src`
