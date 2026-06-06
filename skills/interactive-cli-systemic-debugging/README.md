# Interactive CLI Systemic Debugging

A skills-only Claude Code plugin for systematic debugging of interactive CLI, REPL, TUI, shell wizard, watch-mode, and long-running terminal programs with tmux.

The skill teaches Claude to preserve a live terminal process, observe real screen state, send controlled inputs, capture evidence, and change one debugging variable at a time.

## Installation

First, add this repository as a marketplace source:

```bash
/plugin marketplace add Esonhugh/Marketplace
```

Then install the plugin:

```bash
/plugin install interactive-cli-systemic-debugging@Esonhugh-Marketplace
```

## When It Activates

The skill should activate when a task involves:

- Interactive CLIs, REPLs, TUIs, prompt loops, shell wizards, or installers
- Commands that hang, freeze, wait for input, or need multiple inputs
- Watch mode, dev servers, long-running test runners, or live progress tools
- Terminal rendering, key handling, `$TERM`, dimensions, color, or alternate-screen issues
- Debugging that needs tmux panes, `capture-pane`, `send-keys`, or preserved screen state

Example prompts:

```text
The CLI hangs after printing Continue?. Debug it without changing code yet.
My curses TUI breaks in a small terminal. Reproduce and diagnose it.
The watch mode only fails after I answer the prompt. Keep it alive while testing.
```

## Included Skill

| Skill | Path | Purpose |
|---|---|---|
| `interactive-cli-systemic-debugging` | `skills/interactive-cli-systemic-debugging/SKILL.md` | tmux-based observation workflow for interactive terminal debugging |

## Repository Layout

```text
skills/interactive-cli-systemic-debugging/
├── SKILL.md      # Skill definition
├── README.md     # English overview
├── README-zh.md  # Chinese overview
└── evals.json    # Example evaluation prompts
```

## Notes

- This is a pure skills plugin: the marketplace entry uses `source: "./"` and lists `./skills/interactive-cli-systemic-debugging` in its `skills` array.
- No scripts or MCP servers are bundled. The workflow relies on standard `tmux` commands available in the user's environment.

## License

MIT — Author: Esonhugh
