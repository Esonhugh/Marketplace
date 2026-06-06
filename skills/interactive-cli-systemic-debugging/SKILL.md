---
name: interactive-cli-systemic-debugging
description: This skill should be used when a user asks to debug an interactive CLI, REPL, TUI, prompt loop, shell wizard, watch mode, long-running terminal process, or any command that hangs, waits for input, redraws incorrectly, needs multiple inputs, behaves differently in a real terminal, or requires comparing tmux panes. Trigger on phrases like “it hangs after Continue?”, “the prompt never appears,” “my curses UI breaks in a small terminal,” “the watcher only fails after I answer the prompt,” or “inspect pane 2.”
---

# Interactive CLI Systemic Debugging

## Overview

Use tmux as an observation lab for interactive terminal programs. Preserve the live process, inspect real screen state, send controlled input, capture evidence, and change one variable at a time.

Interactive CLI failures often disappear when forced into a single `Bash` call because prompts, timing, ANSI rendering, stdin state, and background output matter. tmux keeps those signals visible and makes the debugging loop reproducible.

## When to Use

Apply this workflow for:

- Interactive CLIs, REPLs, TUIs, shell wizards, installers, login flows, prompts, and menus.
- Commands that hang, freeze, wait for input, redraw the screen, or stream output for a long time.
- Watchers, dev servers, background monitors, test runners in watch mode, and tools with live progress.
- Bugs involving terminal size, colors, cursor movement, alternate screen mode, raw mode, stdin, or signal handling.
- Cases where a normal one-shot shell command loses context or hides what the user would actually see.

Do not use tmux for a simple deterministic command that exits quickly and has complete stdout/stderr evidence. Run the command normally instead.

## Core Workflow

### 1. State the debugging target

Before starting tmux, write down:

- The exact command or entry point.
- The expected behavior.
- The observed wrong behavior.
- The first hypothesis or unknown to test.

If the target is unclear, ask one focused question or inspect the project enough to identify the command.

### 2. Start a named tmux session

Use a descriptive, collision-resistant name:

```bash
tmux new-session -d -s cli-debug-<topic> -x 120 -y 40
```

Prefer a stable 120x40 viewport unless the bug is size-dependent. For size bugs, record the chosen dimensions.

### 3. Launch the target inside tmux

Send commands exactly as a user would type them:

```bash
tmux send-keys -t cli-debug-<topic> '<command>' Enter
```

Avoid piping input or adding flags that change interactivity unless that is the hypothesis being tested.

### 4. Observe before acting

Capture the pane before sending more input:

```bash
tmux capture-pane -p -t cli-debug-<topic> -S -200
```

Read the captured output as evidence. Look for prompts, partial lines, cursor position clues, warnings, stack traces, progress states, and whether the process is waiting for input.

### 5. Interact deliberately

Send one input at a time, then recapture:

```bash
tmux send-keys -t cli-debug-<topic> 'help' Enter
tmux capture-pane -p -t cli-debug-<topic> -S -200
```

For special keys, use tmux key names:

```bash
tmux send-keys -t cli-debug-<topic> C-c
tmux send-keys -t cli-debug-<topic> Escape
tmux send-keys -t cli-debug-<topic> Down Enter
```

Wait for the program to react before the next input. If timing matters, use short sleeps only as observation delays, not as proof of correctness.

### 6. Save important evidence

When an observation matters, save it to a file:

```bash
tmux capture-pane -p -t cli-debug-<topic> -S -1000 > /tmp/cli-debug-<topic>.log
```

Reference saved logs or relevant excerpts when explaining findings. Evidence should support every conclusion about what happened.

### 7. Change one variable at a time

Keep separate panes or sessions for comparisons:

```bash
tmux split-window -h -t cli-debug-<topic>
tmux list-panes -t cli-debug-<topic>
tmux send-keys -t cli-debug-<topic>.1 '<variant-command>' Enter
```

Confirm pane IDs with `tmux list-panes` before targeting a specific pane. Change only one factor per run: environment variable, terminal size, command flag, input sequence, dependency version, config file, or code change. If two things changed, the result cannot identify the cause.

### 8. Close the loop

For each debugging pass, record:

- Command/session/pane used.
- Inputs sent.
- Observed output.
- Hypothesis supported or refuted.
- Next smallest test.

Stop when the root cause is identified, the issue is reproduced reliably, or the next step requires user input.

## Quick Reference

| Need | Command |
| --- | --- |
| Create detached session | `tmux new-session -d -s <name> -x 120 -y 40` |
| Run a command | `tmux send-keys -t <name> '<command>' Enter` |
| Capture recent output | `tmux capture-pane -p -t <name> -S -200` |
| Capture full scrollback | `tmux capture-pane -p -t <name> -S -` |
| Send Ctrl-C | `tmux send-keys -t <name> C-c` |
| Resize session | `tmux resize-window -t <name> -x <cols> -y <rows>` |
| Split pane | `tmux split-window -h -t <name>` |
| List panes | `tmux list-panes -t <name>` |
| Kill session | `tmux kill-session -t <name>` |

## Debugging Patterns

### Hung command or silent terminal

Capture first. If the screen shows a prompt or cursor after a partial line, the process may be waiting for input rather than hung. Test with harmless input such as `Enter`, `?`, or `help` only when appropriate for the program.

If no screen change occurs, check process state from outside tmux with ordinary diagnostic commands, then return to tmux for user-visible behavior.

### Interactive prompt flow

Treat prompts as a state machine. Capture each state, send exactly one answer, and capture the next state. Do not paste a whole script of answers until the prompt sequence is known.

### TUI rendering or key handling issue

Record terminal size, `$TERM`, color mode, and whether the program uses alternate screen mode. Use tmux resizing to reproduce layout issues. Send named keys through tmux rather than embedding escape sequences by hand.

### Watch mode or dev server

Start the watcher in tmux, capture the ready state, trigger one external change, then capture the reaction. Keep the watcher alive while editing or running client commands in another pane or normal shell.

### Flaky behavior

Run repeated attempts in fresh sessions or panes with the same viewport and environment. Save logs per attempt. Compare the earliest divergence rather than only the final error.

## Common Mistakes

| Mistake | Better approach |
| --- | --- |
| Running the CLI in one `Bash` call and guessing why it hung | Start it in tmux and capture the live pane |
| Sending multiple inputs before observing | Send one input, capture, then decide |
| Treating lack of output as proof of a freeze | Check whether the program is waiting for input or drawing in alternate screen mode |
| Changing flags, env, code, and terminal size at once | Change one variable per pass |
| Losing evidence after the session scrolls | Save `capture-pane` output when it matters |
| Leaving sessions running after debugging | Kill sessions once evidence is saved, unless the user needs them kept alive |

## Reporting Format

When reporting results, include:

1. **Session:** tmux session/pane names and command launched.
2. **Observed:** concise evidence from captured output.
3. **Interpretation:** what the observation proves and what it does not prove.
4. **Next step:** the next smallest experiment, fix, or question.
5. **Cleanup:** whether the tmux session was killed or intentionally left running.

Avoid claiming a fix works until the relevant behavior has been reproduced and observed in tmux or another appropriate verification path.
