# terminal-session-mcp

PTY-backed terminal session MCP for Claude Code.

## Features

- Long-running terminal sessions that do not block MCP tool calls
- Interactive text input and special key input
- Multi-session concurrency
- Terminal resize support
- Full bidirectional transcript recording
- Markdown, text, ANSI, and JSONL transcript export
- `uv`-powered stdio MCP launch

## Requirements

- macOS or Linux
- [`uv`](https://docs.astral.sh/uv/) available on `PATH`
- Python 3.11+ installable by `uv`

## Install

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

## Examples

### Python REPL

Ask Claude:

```text
Use terminal-session MCP to start `python -i`, send `1+1`, read the result, send Ctrl-D, and export the transcript.
```

### Long-running command

```text
Use terminal-session MCP to start `sleep 9999`, verify it is running, terminate it, and export the transcript.
```

### Multi-session

```text
Use terminal-session MCP to start `python -i` labeled py and `sh` labeled shell. Send commands to both, read both outputs, and export both transcripts.
```

## Storage

Session records are written under the current workspace:

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

All input and output are recorded exactly as debugging evidence. This plugin does not redact, mask, block, allowlist, or safety-filter terminal content.

## Platform Support

MVP supports macOS and Linux. Windows ConPTY support is not included yet.

## Limitations

- Does not attach to existing terminal tabs or tmux panes.
- Does not implement a full TUI screen model.
- Does not recover active PTY control after MCP server restart.
- Does not automatically record unrelated Bash tool calls.
