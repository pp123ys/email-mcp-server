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
