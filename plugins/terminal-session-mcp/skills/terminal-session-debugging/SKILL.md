---
name: terminal-session-debugging
description: Use when debugging interactive CLI, REPL, TUI, ssh, telnet, nc, watch-mode, dev server, long-running command, terminal prompt flow, or any command that may not exit. Provides a PTY-backed MCP workflow for spawning terminal sessions, sending text and keys, reading output, managing multiple sessions, and exporting full transcripts.
---

# Terminal Session Debugging

Use the `terminal-session` MCP server for terminal programs that need real PTY behavior or may not exit.

## When to Use

Use this workflow for:

- Interactive CLIs, REPLs, shell prompts, installers, wizards, and prompt loops.
- TUI/curses programs where terminal size and key handling matter.
- `ssh`, `telnet`, `nc`, and other bidirectional terminal/network sessions.
- Watch-mode tools, dev servers, and commands that may run forever.
- Multi-session debugging such as server + client, listener + connector, REPL + shell.
- Any task where a normal Bash call may block, hide prompts, or lose interaction history.

## Core Workflow

1. Call `health_check` to confirm the MCP server is available.
2. Call `spawn_terminal` with a clear `label`.
3. Call `read_terminal` to observe initial output.
4. Send one input at a time with `send_text` or `send_key`.
5. Read after every input before deciding the next action.
6. Use `terminal_status` and `list_terminals` to inspect state.
7. Use `resize_terminal` when terminal dimensions matter.
8. Use `close_terminal` to interrupt, send EOF, terminate, or kill sessions.
9. Call `export_transcript` before reporting final results.

## Recording Model

The MCP records command, output, stdin text, key events, resize events, close events, exit status, and errors under `.terminal-debug/`. It does not redact, mask, block, or safety-filter commands or content. Treat transcripts as complete debugging evidence.

## Interaction Discipline

- Do not send a long script of answers until the prompt sequence is known.
- For prompt flows, treat each prompt as a state; capture, send one response, capture again.
- For multiple sessions, use labels such as `server`, `client`, `listener`, `repl`, or `ssh`.
- Never claim a behavior happened unless it appears in `read_terminal`, `terminal_status`, or the exported transcript.

## Report Format

When reporting results, include:

- Session IDs and labels.
- Commands spawned.
- Inputs and keys sent.
- Observed output evidence.
- Interpretation of what the evidence proves.
- Transcript export paths.
- Cleanup status for active sessions.
