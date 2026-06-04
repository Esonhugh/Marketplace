# Detective — Investigation-Driven Problem Solving

A Claude Code plugin that implements a general-purpose AI problem-solving framework based on detective investigation methodology. Every problem is a **case**; every conclusion is backed by a traceable **evidence chain**.

## Core Concept

The AI maintains a **CaseBoard** — a directed labeled graph of **Fragments** (unified case entities) and **Threads** (logical connections). In shipped v2, the primary interface is the local MCP graph core for project-local case state, graph overview/query, shortest-path lookup, and Markdown/Mermaid exports.

```text
Current shipped v2 MCP core: local case storage + graph state + graph overview/query + shortest paths + exports
Legacy v1 workflow label: Scan → Evolve → Focus → Act → File
Current v2.1 orchestration support: scheduler memory + signals + specialist agents built on the MCP graph core
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

- **MCP Graph Core**: Project-local case storage, graph overview/search, shortest paths, and Markdown/Mermaid exports
- **Legacy Strategy Helpers**: v1 scoring, constraint propagation, direction pruning, and convergence helpers remain available as CLI compatibility wrappers over shared `detective_mcp` utilities
- **Case Discussion**: Structured human-AI collaboration at deadlocks, ambiguity, or critical moments
- **Full Traceability**: Every conclusion links back through evidence to initial observations

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

## v2 MCP Graph Core

Detective v2 includes a local stdio MCP server registered by `.mcp.json` and launched with `uv`. The v2 MCP graph core is the canonical current architecture, and the MCP server is the preferred state interface for new workflows.

## v2.1 Autonomous Investigation

Detective v2.1 adds orchestration support on top of the MCP graph core.

New capabilities:

- Case-local scheduler memory for attempted directions and next actions
- Candidate action scoring
- Cold direction detection
- User guidance capture with priority over automation
- Conservative convergence status
- Deadlock status
- Specialist agents for hypotheses, evidence, contradictions, graph paths, and reporting

Default autonomy is `full_auto`, but user intervention always takes priority. The MCP server remains the state owner; agents and skills must use MCP tools rather than editing `.detective/` files directly.

Core tools:

- `detective_open_case`
- `detective_load_case`
- `detective_save_case`
- `detective_graph_overview`
- `detective_add_node`
- `detective_update_node`
- `detective_get_node`
- `detective_list_nodes`
- `detective_search_nodes`
- `detective_add_edge`
- `detective_list_edges`
- `detective_neighbors`
- `detective_shortest_path`
- `detective_export_markdown`
- `detective_export_mermaid`

Canonical state is stored in the current project:

```text
.detective/cases/<case-id>/case.json
```

Generated review artifacts are stored next to it:

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

JSON is the only canonical state source. Markdown and Mermaid are generated projections.
Legacy scripts remain available as thin CLI wrappers over shared detective_mcp utility modules.

## Architecture

```
┌─────────────────────────────────────────────┐
│           Claude Code Session               │
│                                             │
│  ┌─────────┐   ┌──────────┐   ┌────────┐  │
│  │ Skills  │←→│ v2 MCP   │←→│CaseBoard│  │
│  │         │   │Graph Core│   │ (JSON) │  │
│  └─────────┘   └──────────┘   └────────┘  │
│       │              ↑                      │
│       └──── Legacy CLI wrappers ───────────┘
└─────────────────────────────────────────────┘
```

- **v2 MCP Graph Core**: The canonical current architecture for reading and writing project-local case graph state.
- **CaseBoard**: Canonical JSON state at `.detective/cases/<case-id>/case.json`; generated `notes.md`, `graph.mmd`, and `events.jsonl` live beside it.
- **Legacy CLI wrappers**: Older v1-style scripts remain for compatibility and delegate to shared `detective_mcp` utility modules for scoring, constraints, and convergence helpers.
- **Action Executor**: Claude Code itself — bash, file ops, web search, MCP tools.

## Legacy Scoring Compatibility

The older Focus-phase helper logic answered: "What's the single most valuable next action?"

```
Score(action) = (Discrimination × Feasibility) / NormalizedCost
```

In shipped v2, this score is retained only as a legacy compatibility helper layered on shared MCP graph utilities. The shipped MCP graph core provides local case storage, graph state, graph overview/query, shortest-path lookup, and exports; autonomous pruning heuristics are not described as a current core behavior.

## Installation

```bash
# Test locally
claude --plugin-dir /path/to/detective-plugin

# Or symlink into your plugins directory
ln -s /path/to/detective-plugin ~/.claude/plugins/detective
```

## State Storage

Current v2 case state is project-local and stored at:

```text
.detective/cases/<case-id>/case.json
```

Generated review artifacts are stored beside the canonical JSON file:

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

Legacy v1 case files used the flat path `.detective/cases/<case-id>.json`; that path is retained only for compatibility with older data and scripts.

## Applicable Domains

| Domain | Hypotheses Are | Evidence Is |
|--------|---------------|-------------|
| Security Research | Attack vectors | Confirmed vulnerabilities |
| Intelligence Analysis | Candidate explanations | Corroborated intelligence |
| Root Cause Analysis | Failure modes | Diagnostic results |
| Code Archaeology | Design intentions | Code patterns & history |

## Relationship to PoJun

| | PoJun | Detective Framework |
|---|---|---|
| Architecture | Three-process distributed system | Local MCP graph core + compatibility CLI wrappers |
| State | SQLite + HTTP | Project-local JSON case graph |
| Entities | origin/goal/fact/intent | Fragment + Thread (unified) |
| Loop | OODA | Scan-Evolve-Focus-Act-File |
| Strategy | Manual priority + reviewer | Formal scoring + constraint propagation helpers |
| Convergence | LLM judgment with `complete: true` | MCP graph state + convergence/deadlock signals plus legacy compatibility helpers |
| Concurrency | Multiple workers in parallel | Sequential case workflow |
| Domain | CTF/security-focused | Domain-neutral + configuration adaptation |

The Detective framework is a theoretical generalization and lightweight reduction of the PoJun OODA methodology.

## Design Specification

Design specs:

- Current v2.0 MCP graph core: `docs/superpowers/specs/2026-06-03-detective-mcp-graph-core-design.md`
- v2.1 autonomous investigation orchestration: `docs/superpowers/specs/2026-06-03-detective-v2-1-autonomous-investigation-design.md`

## File Structure

```
detective-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── .mcp.json                    # Local MCP server registration
├── .gitignore
├── pyproject.toml               # Python package and uv configuration
├── README.md                    # English documentation
├── README-zh.md                 # Chinese documentation
├── agents/
│   ├── strategy-evaluator.md    # Legacy strategy scoring agent
│   ├── lead-investigator.md     # v2.1 investigation coordinator
│   ├── hypothesis-generator.md  # Hypothesis specialist
│   ├── evidence-hunter.md       # Evidence specialist
│   ├── contradiction-finder.md  # Falsification specialist
│   ├── path-analyzer.md         # Graph topology specialist
│   └── report-writer.md         # Artifact and resolution specialist
├── detective_mcp/               # Shared v2 MCP graph core and utility modules
│   ├── exports.py               # Markdown and Mermaid exports
│   ├── graph.py                 # Graph operations and traversal
│   ├── legacy_board.py          # Legacy board compatibility helpers
│   ├── legacy_convergence.py    # Legacy convergence compatibility helpers
│   ├── legacy_scoring.py        # Legacy scoring compatibility helpers
│   ├── models.py                # Case graph data models
│   ├── server.py                # stdio MCP server tools
│   └── store.py                 # Project-local case storage
├── scripts/                     # Legacy CLI wrappers over detective_mcp utilities
│   ├── board.py
│   ├── scoring.py
│   └── convergence.py
├── skills/
│   ├── brainstorm/SKILL.md      # Pre-investigation problem exploration
│   ├── open-case/SKILL.md       # Case initialization
│   ├── investigate/SKILL.md     # Main loop
│   ├── review-board/SKILL.md    # Board display
│   ├── discuss-case/SKILL.md    # Case discussion
│   └── close-case/SKILL.md      # Resolution
└── tests/                       # MCP core, exports, storage, and legacy wrapper tests
```
