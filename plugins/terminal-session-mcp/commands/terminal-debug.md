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
