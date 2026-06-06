# Terminal Session MCP Design

Date: 2026-06-07
Status: Approved for implementation planning

## Summary

Build `terminal-session-mcp`, a Claude Code marketplace plugin that provides a `uv`-launched stdio MCP server for simulated terminal sessions. The server uses PTY-backed sessions instead of synchronous command execution, so commands that run forever (`ssh`, `telnet`, `nc`, REPLs, TUIs, watch-mode processes, dev servers) do not block MCP tool calls. It supports multiple concurrent terminal sessions, sending text and special keys, resizing terminals, reading incremental output, querying status, closing sessions, and exporting complete bidirectional transcripts.

The plugin prioritizes debugging and replay fidelity. It records all command input, output, key events, resize events, close events, exit status, and errors. It does not perform redaction, masking, command blocking, allowlisting, or security review.

Implementation must be verified with Claude CLI / Claude Code after local Python and MCP tests pass.

## Goals

- Provide a marketplace plugin installable from this repository.
- Run the MCP server over stdio via `uv`.
- Simulate real terminal behavior using PTY on macOS/Linux.
- Support long-running and non-terminating commands without blocking tool calls.
- Support multiple concurrent sessions.
- Support text input and special key input.
- Record all bidirectional interaction content without redaction.
- Persist session events and transcripts under `.terminal-debug/`.
- Provide a skill and slash command so Claude Code knows when and how to use the MCP server.
- Verify the plugin with real Claude CLI / Claude Code MCP tool usage.

## Non-goals for MVP

- Windows ConPTY support.
- tmux backend or attach-to-existing-tmux support.
- Attaching to existing terminal tabs or shells.
- Web replay UI.
- Full terminal screen emulation for complex TUIs.
- Automatic capture of all Claude Code Bash tool calls.
- Security filtering, command blocking, allowlisting, redaction, or masking.
- Recovering active PTY control after MCP server restart.

## Product Shape

Plugin name:

```text
terminal-session-mcp
```

Proposed plugin layout:

```text
plugins/terminal-session-mcp/
  .claude-plugin/
    plugin.json
  .mcp.json
  pyproject.toml
  README.md
  README-zh.md

  terminal_session_mcp/
    __init__.py
    __main__.py
    server.py
    models.py
    session_manager.py
    pty_session.py
    recorder.py
    storage.py
    keymap.py
    ansi.py
    timeutil.py

  skills/
    terminal-session-debugging/
      SKILL.md
      README.md
      README-zh.md

  commands/
    terminal-debug.md

  tests/
    test_keymap.py
    test_ansi.py
    test_storage.py
    test_recorder.py
    test_pty_session.py
    test_session_manager.py
```

## MCP Configuration

The plugin MCP configuration must use `uv` and stdio:

```json
{
  "terminal-session": {
    "command": "uv",
    "args": [
      "--directory",
      "${CLAUDE_PLUGIN_ROOT}",
      "run",
      "python",
      "-m",
      "terminal_session_mcp"
    ],
    "env": {
      "TERMINAL_SESSION_WORKSPACE": "${PWD}"
    }
  }
}
```

Optional environment variables:

- `TERMINAL_SESSION_MAX_ACTIVE`: maximum active sessions, default `16`.
- `TERMINAL_SESSION_WORKSPACE`: storage workspace, default current working directory.

The MCP server must not write ordinary logs to stdout. stdout is reserved for MCP protocol traffic. Logs go to stderr or `.terminal-debug/server.log`.

## Architecture

```text
Claude Code
   |
   | MCP tool calls over stdio
   v
terminal_session_mcp.server
   |
   +-- SessionManager
   |     |
   |     +-- PTYSession term_a
   |     +-- PTYSession term_b
   |     +-- PTYSession term_c
   |
   +-- Recorder
   |     |
   |     +-- events.jsonl
   |     +-- transcript.ansi
   |     +-- transcript.txt
   |
   +-- KeyMap
   |
   +-- Storage
```

### `server.py`

- Starts the stdio MCP server.
- Registers tools.
- Validates tool arguments.
- Delegates all terminal/session work to `SessionManager`.
- Does not directly manipulate PTY file descriptors.
- Does not directly write session files.

### `SessionManager`

- Creates session IDs.
- Maintains the active session registry.
- Routes read/send/status/close calls to the right session.
- Lists active and historical sessions.
- Enforces active session limit.
- Marks stale running metadata as `orphaned` on server restart.

Session IDs use a readable, sortable format:

```text
term_YYYYMMDD_HHMMSS_<random6>
```

### `PTYSession`

Each session owns one PTY-backed child process.

Responsibilities:

- Spawn child command in a PTY.
- Set initial terminal size.
- Run a background output reader.
- Write text and key bytes to the PTY.
- Resize the PTY.
- Close, interrupt, terminate, or kill the child process.
- Notify the `Recorder` of output, input, resize, close, exit, and errors.

The implementation can use `pexpect` for MVP stability, managed by `uv`. Standard-library PTY can be revisited later if minimizing dependencies becomes important.

### `Recorder`

Each session has one recorder.

Responsibilities:

- Assign per-session monotonically increasing `seq` values.
- Append events to an in-memory recent-event buffer.
- Append events to `events.jsonl`.
- Update `transcript.ansi` and `transcript.txt`.
- Update `metadata.json`.
- Provide event reads after `since_seq` with `max_bytes` truncation.

### `Storage`

Responsible for filesystem operations under `.terminal-debug/`:

- Create storage root and session directories.
- Append event logs and transcripts.
- Atomically write `metadata.json` and `index.json`.
- Export Markdown summaries.
- Read historical events if requested `since_seq` is no longer in memory.

### `KeyMap`

Maps key names to bytes. MVP supports:

```text
ENTER TAB ESC BACKSPACE DELETE
UP DOWN LEFT RIGHT HOME END PAGE_UP PAGE_DOWN
CTRL_A through CTRL_Z
F1 through F12
```

Examples:

| Key | Bytes |
|---|---|
| `ENTER` | `\r` |
| `TAB` | `\t` |
| `ESC` | `\x1b` |
| `CTRL_C` | `\x03` |
| `CTRL_D` | `\x04` |
| `CTRL_Z` | `\x1a` |
| `UP` | `\x1b[A` |
| `DOWN` | `\x1b[B` |
| `RIGHT` | `\x1b[C` |
| `LEFT` | `\x1b[D` |

## MCP Tools

### `health_check`

Returns server health and configuration.

Response includes:

- status
- workspace
- storage root
- active session count
- max active sessions
- platform
- PTY backend

### `spawn_terminal`

Starts a command in a new PTY session and returns immediately.

Parameters:

```json
{
  "command": "python -i",
  "cwd": ".",
  "env": {"PYTHONUNBUFFERED": "1"},
  "cols": 120,
  "rows": 40,
  "label": "python-repl"
}
```

Response:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "label": "python-repl",
  "pid": 12345,
  "status": "running",
  "cwd": "/repo",
  "cols": 120,
  "rows": 40,
  "created_at": "2026-06-07T14:30:12.000Z"
}
```

### `read_terminal`

Reads already-recorded events after `since_seq`. It does not wait for process exit.

Parameters:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "since_seq": 0,
  "max_bytes": 20000,
  "strip_ansi": true,
  "include_input": false
}
```

Response includes events, `latest_seq`, `session_latest_seq`, truncation flag, and session status.

### `send_text`

Writes text to a session PTY and records the exact text.

Parameters:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "text": "1+1",
  "submit": true
}
```

If `submit` is true, the implementation appends `\r` to the bytes sent. The event records `submit: true`; it does not mask or redact text.

### `send_key`

Writes a special key sequence to the PTY and records the key event.

Parameters:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "key": "CTRL_C"
}
```

### `resize_terminal`

Changes PTY rows/columns and records the resize event.

Parameters:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "cols": 80,
  "rows": 24
}
```

### `terminal_status`

Returns status and metadata for one session.

Response includes:

- session ID and label
- pid
- status
- exit code
- cwd
- cols/rows
- timestamps
- duration
- latest sequence
- last output time
- reader status
- storage path
- output byte count
- event count

Statuses:

```text
starting running exited closed failed orphaned
```

### `close_terminal`

Requests session close.

Parameters:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "mode": "terminate"
}
```

Modes:

| Mode | Behavior |
|---|---|
| `interrupt` | Send Ctrl-C |
| `eof` | Send Ctrl-D |
| `terminate` | Send SIGTERM |
| `kill` | Send SIGKILL |

The tool returns after issuing the close action. It does not wait forever for process exit.

### `list_terminals`

Lists active and optionally historical sessions.

Parameters:

```json
{
  "include_closed": true
}
```

### `export_transcript`

Exports complete transcript in one of:

```text
jsonl text ansi markdown
```

Parameters:

```json
{
  "session_id": "term_20260607_143012_a1b2c3",
  "format": "markdown"
}
```

Returns exported path and byte count.

### Optional: `summarize_terminal`

May generate deterministic `summary.md` from events. It must not call an LLM inside the MCP server. If not implemented, `export_transcript(format="markdown")` is sufficient for MVP.

## Data Model and Persistence

Storage root:

```text
.terminal-debug/
  index.json
  server.log
  sessions/
    term_20260607_143012_a1b2c3/
      metadata.json
      events.jsonl
      transcript.ansi
      transcript.txt
      summary.md
```

### `index.json`

Global session index:

```json
{
  "version": 1,
  "updated_at": "2026-06-07T14:31:55.123Z",
  "sessions": [
    {
      "session_id": "term_20260607_143012_a1b2c3",
      "label": "server",
      "command": "python -m http.server 8000",
      "status": "running",
      "created_at": "2026-06-07T14:30:12.000Z",
      "ended_at": null,
      "path": "sessions/term_20260607_143012_a1b2c3"
    }
  ]
}
```

### `metadata.json`

Session metadata:

```json
{
  "version": 1,
  "session_id": "term_20260607_143012_a1b2c3",
  "label": "server",
  "command": "python -m http.server 8000",
  "cwd": "/Users/me/project",
  "env": {"PYTHONUNBUFFERED": "1"},
  "pid": 12345,
  "cols": 120,
  "rows": 40,
  "status": "running",
  "exit_code": null,
  "created_at": "2026-06-07T14:30:12.000Z",
  "ended_at": null,
  "latest_seq": 17,
  "last_output_at": "2026-06-07T14:30:20.000Z",
  "output_bytes": 1024,
  "event_count": 17
}
```

### `events.jsonl`

Per-session event stream. Every event has:

- `seq`
- `ts`
- `type`
- `session_id`

Event types:

- `spawn`
- `output`
- `input_text`
- `input_key`
- `resize`
- `close`
- `exit`
- `error`
- `orphaned`

Example:

```jsonl
{"seq":1,"ts":"2026-06-07T14:30:12.000Z","type":"spawn","session_id":"term_...","command":"python -i","cwd":"/repo","pid":12345,"cols":120,"rows":40,"label":"python-repl"}
{"seq":2,"ts":"2026-06-07T14:30:12.123Z","type":"output","session_id":"term_...","stream":"pty","text":">>> ","bytes":4}
{"seq":3,"ts":"2026-06-07T14:30:13.000Z","type":"input_text","session_id":"term_...","text":"1+1","submit":true,"bytes":4}
{"seq":4,"ts":"2026-06-07T14:30:13.050Z","type":"output","session_id":"term_...","stream":"pty","text":"2\n>>> ","bytes":6}
{"seq":5,"ts":"2026-06-07T14:30:14.000Z","type":"input_key","session_id":"term_...","key":"CTRL_D","bytes":1}
{"seq":6,"ts":"2026-06-07T14:30:14.100Z","type":"exit","session_id":"term_...","exit_code":0}
```

PTY output uses UTF-8 decode with `errors="replace"` for text view. Raw/ANSI transcript is retained separately.

## Data Flows

### Spawn flow

```text
Claude calls spawn_terminal
  -> server validates args
  -> SessionManager creates session_id
  -> Storage creates session directory
  -> PTYSession starts child process in PTY
  -> Recorder writes spawn event
  -> PTYSession starts reader task/thread
  -> return session_id immediately
```

### Output flow

```text
Child writes terminal output
  -> PTY master receives bytes
  -> reader reads bytes
  -> bytes decode to text
  -> Recorder writes output event
  -> transcripts and metadata update
```

### Input flow

```text
Claude calls send_text/send_key
  -> SessionManager finds running session
  -> PTYSession writes bytes
  -> Recorder writes input_text/input_key event
  -> tool returns bytes_written + recorded_seq
```

### Read flow

```text
Claude calls read_terminal
  -> SessionManager finds live or historical session
  -> Recorder/Storage reads events after since_seq
  -> max_bytes/include_input/strip_ansi applied
  -> return events and status
```

### Close flow

```text
Claude calls close_terminal
  -> close event recorded
  -> PTYSession sends Ctrl-C/Ctrl-D/SIGTERM/SIGKILL
  -> tool returns current/closing status
  -> reader/waiter eventually records exit
```

## Error Handling and Recovery

Standard error shape:

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "No terminal session found: term_...",
    "recoverable": false,
    "hint": "Call list_terminals to inspect available sessions."
  }
}
```

Error codes:

| Code | Meaning |
|---|---|
| `INVALID_ARGUMENT` | Invalid tool argument |
| `SESSION_NOT_FOUND` | Session does not exist |
| `SESSION_NOT_RUNNING` | Session cannot receive input |
| `SPAWN_FAILED` | PTY/shell spawn failed |
| `READ_FAILED` | Event or PTY read failed |
| `WRITE_FAILED` | PTY write failed |
| `INVALID_KEY` | Unsupported key |
| `INVALID_SIZE` | Invalid rows/cols |
| `CWD_NOT_FOUND` | cwd does not exist |
| `EXPORT_FAILED` | transcript export failed |
| `STORAGE_FAILED` | required logging failed |
| `SESSION_LIMIT_EXCEEDED` | max active sessions reached |

Rules:

- Tool calls must not wait forever.
- One failed session must not affect other sessions.
- Errors inside an existing session should be recorded as `error` events.
- If storage fails before spawn, do not start the command.
- If storage fails during a running session, mark the session failed and attempt to close it. Continuing without recording violates the product goal.
- On MCP server restart, previously `running` sessions are marked `orphaned` because PTY control cannot be restored in MVP.

## Skill Integration

Add skill:

```text
skills/terminal-session-debugging/SKILL.md
```

Frontmatter:

```markdown
---
name: terminal-session-debugging
description: Use when debugging interactive CLI, REPL, TUI, ssh, telnet, nc, watch-mode, dev server, long-running command, terminal prompt flow, or any command that may not exit. Provides a PTY-backed MCP workflow for spawning terminal sessions, sending text and keys, reading output, managing multiple sessions, and exporting full transcripts.
---
```

Skill guidance:

- Use the MCP for interactive or long-running commands.
- Prefer `spawn_terminal` over Bash for commands that may not exit.
- Use labels for multi-session debugging.
- Read output after every input/key event.
- Send one state transition at a time for prompt flows.
- Use `terminal_status`, `list_terminals`, and `export_transcript` for inspection.
- Report only observed evidence.
- Export transcripts before final debugging reports.
- Do not promise safety filtering or redaction; all content is recorded as debugging evidence.

## Slash Command Integration

Add command:

```text
commands/terminal-debug.md
```

Frontmatter and body:

```markdown
---
description: Start a terminal-session MCP debugging workflow for an interactive or long-running command.
argument-hint: <command or debugging goal>
---

Use the terminal-session MCP to debug this command or scenario: $ARGUMENTS

Workflow:
1. Call health_check.
2. Spawn a terminal session with a clear label.
3. Read initial output.
4. Interact step by step using send_text/send_key.
5. Use terminal_status/list_terminals as needed.
6. Export transcript before finishing.
```

## Documentation and Marketplace Integration

Add plugin docs:

- `plugins/terminal-session-mcp/README.md`
- `plugins/terminal-session-mcp/README-zh.md`

Docs must cover:

- What the plugin does.
- Installation.
- MCP tools.
- Example workflows for REPL, ssh/telnet/nc, and server+client sessions.
- Storage layout.
- Claude CLI verification examples.
- Platform support.
- MVP limitations.

Update root marketplace docs:

- `README.md`
- `README-zh.md`

Add catalog rows and plugin descriptions.

English catalog row:

```markdown
| [terminal-session-mcp](#terminal-session-mcp) | Development | Esonhugh | local | PTY terminal session MCP for long-running interactive CLI debugging and full transcript recording |
```

Chinese catalog row:

```markdown
| [terminal-session-mcp](#terminal-session-mcp) | 开发 | Esonhugh | 本地 | 基于 PTY 的终端会话 MCP，支持长命令、交互式 CLI 调试和完整记录 |
```

## Testing and Acceptance

### Unit tests

Use `pytest` for:

- key mapping
- ANSI stripping
- storage creation and writes
- recorder event order and transcript updates
- metadata/index updates

### PTY integration tests

Required scenarios:

1. Short command: `echo hello`.
2. REPL: `python -i`, send `1+1`, read `2`, exit with Ctrl-D.
3. Long command: `sleep 9999`, confirm spawn returns, terminate.
4. Multi-session: `python -i` plus `sh`, interact with both and confirm outputs do not mix.
5. Key input: send Ctrl-D/Ctrl-C and confirm event/status.
6. Resize: resize PTY and confirm metadata and event.

### MCP stdio tests

Verify:

- `uv run python -m terminal_session_mcp` starts the server.
- No ordinary stdout logs pollute the MCP protocol.
- Tools are exposed and callable through an MCP client/inspector if available.

### Claude CLI / Claude Code real verification

This is a hard acceptance gate after implementation.

Required Claude CLI scenarios:

1. Health check:
   ```text
   Use terminal-session MCP health_check and report the result.
   ```

2. Short command:
   ```text
   Use terminal-session MCP to spawn `echo hello-terminal-mcp`, read the output, check status, and export the transcript.
   ```

3. Python REPL:
   ```text
   Use terminal-session MCP to start `python -i`, wait for the prompt, send `1+1` with Enter, read the result, then send Ctrl-D and export the transcript.
   ```

4. Long command:
   ```text
   Use terminal-session MCP to start `sleep 9999`, verify it is running, then terminate it and check final status.
   ```

5. Multi-session concurrency:
   ```text
   Use terminal-session MCP to start two sessions: `python -i` labeled py and `sh` labeled shell. In py send `10*10`; in shell send `echo shell-ok`; read both outputs and export both transcripts.
   ```

6. Key and prompt flow:
   ```text
   Use terminal-session MCP to start `sh`, send `echo before`, press Enter, then send Ctrl-C, then send `echo after`, press Enter, and read the transcript.
   ```

Acceptance criteria:

- `uv run pytest` passes.
- The MCP server starts under `uv`.
- Claude CLI loads the plugin MCP server.
- Claude CLI can call the tools.
- REPL, long command, key input, multi-session, and transcript export all work.
- `.terminal-debug` contains complete metadata, events, and transcripts.
- No stdout log pollution breaks stdio MCP.
- If any verification fails, report the failure and output instead of claiming success.

## Roadmap

### Phase 2: Screen capture

Add `capture_screen(session_id)` backed by a terminal emulator such as `pyte`, returning current screen buffer and cursor state.

### Phase 3: tmux backend

Optional backend for persistent sessions and attach/recovery:

```text
backend = "pty" | "tmux"
```

### Phase 4: record/replay

Export replay scripts or implement transcript replay from `events.jsonl`.

### Phase 5: analysis tools

Add:

- `search_transcript`
- `extract_prompts`
- `find_errors`
- `diff_sessions`
- `compare_transcripts`

### Phase 6: resource controls

Add optional log rotation and configurable output/session limits.

### Phase 7: Windows support

Implement ConPTY support for Windows.
