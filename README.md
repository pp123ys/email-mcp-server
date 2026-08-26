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
