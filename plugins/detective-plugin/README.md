# Detective — Investigation-Driven Problem Solving

A Claude Code plugin that implements a general-purpose AI problem-solving framework based on detective investigation methodology. Every problem is a **case**; every conclusion is backed by a traceable **evidence chain**.

## Core Concept

The AI maintains a **CaseBoard** — a directed labeled graph of **Fragments** (unified case entities) and **Threads** (logical connections) — and solves problems through a detective's investigation loop:

```
Scan → Evolve → Focus → Act → File → (loop until convergence)
```

## The Fragment + Thread Model

The board has only two primitives:

**Fragment** — a single case information unit described by two dimensions:

| Dimension | Values | Meaning |
|-----------|--------|---------|
| Maturity | Raw → Clue → Evidence → Anchor | How certain the information is |
| Role | Observation, Hypothesis, Constraint, Conclusion | What function it serves in reasoning |

**Thread** — a directed labeled edge between fragments:

| Type | Meaning |
|------|---------|
| `supports` | Source provides evidence for target |
| `contradicts` | Source conflicts with target |
| `derives` | Target was derived from source |
| `eliminates` | Source definitively disproves target |
| `requires` | Target depends on source |

## Key Features

- **Strategy Engine**: Information-gain scoring (`Discrimination × Feasibility / Cost`), constraint propagation, direction pruning, automatic phase detection
- **Autonomous Convergence**: The system knows when it's "done" — when the graph topology satisfies formal convergence criteria
- **Case Discussion**: Structured human-AI collaboration at deadlocks, ambiguity, or critical moments
- **Full Traceability**: Every conclusion links back through evidence to initial observations
- **Phase Auto-Detection**: Board topology automatically determines investigation phase (Opening → Survey → Pursuit → Convergence → Closing → Resolution)

## Usage

```
/detective:brainstorm
/detective:open-case "Investigate the root cause of this performance regression"
/detective:investigate
/detective:review-board
/detective:discuss-case
/detective:close-case
```

| Skill | Purpose |
|-------|---------|
| `brainstorm` | Collaborative problem exploration before opening a case |
| `open-case` | Initialize a new investigation, define crime scene and goal |
| `investigate` | Run the Scan→Evolve→Focus→Act→File loop |
| `review-board` | Display CaseBoard state, fragments, threads, hypotheses |
| `discuss-case` | Structured discussion at key decision points |
| `close-case` | Produce resolution with complete evidence chain |

## Architecture

```
┌─────────────────────────────────────────────┐
│           Claude Code Session               │
│                                             │
│  ┌─────────┐   ┌──────────┐   ┌────────┐  │
│  │CaseBoard│   │ Strategy │   │ Action │  │
│  │  (JSON) │←→│  Engine  │──→│Executor│  │
│  └─────────┘   └──────────┘   └────────┘  │
│       ↑              ↑                      │
│       └──── Skills ──┘                      │
└─────────────────────────────────────────────┘
```

- **CaseBoard**: A JSON file (`.detective/cases/<id>.json`) — the investigation board
- **Strategy Engine**: Python scripts for scoring, constraint propagation, convergence detection
- **Action Executor**: Claude Code itself — bash, file ops, web search, MCP tools

## Strategy Engine

The Focus phase answers: "What's the single most valuable next action?"

```
Score(action) = (Discrimination × Feasibility) / NormalizedCost
```

Pruning heuristics automatically eliminate:
- Actions targeting eliminated hypotheses (dead target)
- Actions whose outcome would duplicate existing evidence (redundancy)
- Directions attempted 3+ times without progress (cold lead)
- Circular reasoning chains

## Installation

```bash
# Test locally
claude --plugin-dir /path/to/detective-plugin

# Or symlink into your plugins directory
ln -s /path/to/detective-plugin ~/.claude/plugins/detective
```

## State Storage

Case files are project-local: `.detective/cases/<case-id>.json`

Each case file contains the complete board state and is self-contained for portability.

## Applicable Domains

| Domain | Hypotheses Are | Evidence Is |
|--------|---------------|-------------|
| Security Research | Attack vectors | Confirmed vulnerabilities |
| Intelligence Analysis | Candidate explanations | Corroborated intelligence |
| Root Cause Analysis | Failure modes | Diagnostic results |
| Code Archaeology | Design intentions | Code patterns & history |

## Design Specification

Full theoretical model: `docs/superpowers/specs/2026-05-06-detective-framework-design.md`

## File Structure

```
detective-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── .gitignore
├── README.md                    # English documentation
├── README-zh.md                 # Chinese documentation
├── agents/
│   └── strategy-evaluator.md    # Strategy scoring agent
├── scripts/
│   ├── board.py                 # CaseBoard CRUD
│   ├── scoring.py               # Scoring & constraints
│   └── convergence.py           # Convergence detection
└── skills/
    ├── brainstorm/SKILL.md      # Pre-investigation problem exploration
    ├── open-case/SKILL.md       # Case initialization
    ├── investigate/SKILL.md     # Main loop
    ├── review-board/SKILL.md    # Board display
    ├── discuss-case/SKILL.md    # Case discussion
    └── close-case/SKILL.md      # Resolution
```
