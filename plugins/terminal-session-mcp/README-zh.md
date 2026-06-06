# terminal-session-mcp

面向 Claude Code 的 PTY 终端会话 MCP。

## 功能

- 长时间运行命令不会阻塞 MCP tool call
- 支持交互式文本输入和特殊按键输入
- 支持多 session 并发
- 支持终端 resize
- 完整记录双向交互 transcript
- 支持 Markdown、text、ANSI、JSONL 导出
- 通过 `uv` 以 stdio MCP 方式启动

## 依赖

- macOS 或 Linux
- [`uv`](https://docs.astral.sh/uv/) 可在 `PATH` 中访问
- 可由 `uv` 安装/使用的 Python 3.11+

## 安装

```bash
/plugin install terminal-session-mcp@Esonhugh-Marketplace
```

## MCP Tools

- `health_check`
- `spawn_terminal`
- `read_terminal`
- `send_text`
- `send_key`
- `resize_terminal`
- `terminal_status`
- `close_terminal`
- `list_terminals`
- `export_transcript`

## 示例

### Python REPL

```text
Use terminal-session MCP to start `python -i`, send `1+1`, read the result, send Ctrl-D, and export the transcript.
```

### 长时间运行命令

```text
Use terminal-session MCP to start `sleep 9999`, verify it is running, terminate it, and export the transcript.
```

### 多 session

```text
Use terminal-session MCP to start `python -i` labeled py and `sh` labeled shell. Send commands to both, read both outputs, and export both transcripts.
```

## 存储

记录保存在当前 workspace：

```text
.terminal-debug/
  index.json
  sessions/<session_id>/
    metadata.json
    events.jsonl
    transcript.ansi
    transcript.txt
    summary.md
```

所有输入和输出都会作为调试证据原样记录。本插件不做打码、脱敏、拦截、allowlist 或安全过滤。

## 平台支持

MVP 支持 macOS 和 Linux。暂不支持 Windows ConPTY。

## 限制

- 不附着已有 terminal tab 或 tmux pane。
- 不实现完整 TUI screen model。
- MCP server 重启后不恢复活跃 PTY 控制。
- 不自动记录无关 Bash tool call。
