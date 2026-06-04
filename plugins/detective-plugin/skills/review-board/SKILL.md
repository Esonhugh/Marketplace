---
name: review-board
description: This skill should be used when the user asks to "review the board", "show the case status", "what's on the board", "show investigation progress", "display the case", or wants to see the current state of their investigation CaseBoard.
---

# Review Board — Display Investigation State

Present the current CaseBoard state in a human-readable format, showing all fragments, threads, hypotheses, and the investigation's overall progress.

## MCP-first review

For Detective v2 cases, prefer MCP tools:

1. `detective_graph_overview`
2. `detective_list_nodes`
3. `detective_list_edges`
4. `detective_convergence_status`
5. `detective_export_markdown`
6. `detective_export_mermaid`

Only use legacy scripts if the MCP server is unavailable.

## Legacy v1 fallback process

Use this section only for legacy v1 flat JSON case files when the Detective MCP server is unavailable. For v2/v2.1 cases, use the MCP-first review flow above.

### 1. Load Legacy Board State

```bash
python $PLUGIN_ROOT/scripts/board.py status .detective/cases/<case-id>.json
python $PLUGIN_ROOT/scripts/scoring.py suggest-phase .detective/cases/<case-id>.json
python $PLUGIN_ROOT/scripts/convergence.py .detective/cases/<case-id>.json
```

Also read the full case file to access fragment details:
```bash
cat .detective/cases/<case-id>.json
```

### 2. Present the Board

Display in this structured format:

```
## Case: <title>
**Phase**: <current phase> | **Actions**: <taken>/<budget> | **Converged**: <yes/no>

### Active Hypotheses (<count>)
| ID | Description | Confidence | Supporting | Contradicting |
|----|-------------|------------|------------|---------------|
| <id> | <content> | <conf>    | <count>    | <count>       |

### Eliminated Hypotheses (<count>)
| ID | Description | Reason |
|----|-------------|--------|
| <id> | <content> | <elimination_reason> |

### Evidence Chain (<count> pieces)
- [Anchor] <content> (source: <source>)
- [Evidence] <content> (source: <source>)
- [Clue] <content> (needs verification)

### Constraints (<count> active)
- <constraint content> → eliminates: <hypothesis ids>

### Key Connections
- <from> --<type>--> <to> (most important threads)

### Investigation Log (last 5 actions)
- Round N: <action description> → <outcome>
```

### 3. Provide Assessment

After the board display, add a brief analytical summary:
- What's going well (strong evidence chains)
- What's concerning (unsupported hypotheses, isolated fragments)
- Suggested next step
- Whether a case discussion might be helpful

## Graph Export (Optional)

If the user asks for a visual/graph representation:

```bash
python $PLUGIN_ROOT/scripts/board.py export-graph .detective/cases/<case-id>.json
```

This outputs DOT format which can be rendered with Graphviz.

## Legacy v1 multiple-case fallback

For legacy v1 flat JSON case files only, if multiple files exist and MCP is unavailable, ask the user which legacy case to inspect.

## Legacy v1 fallback resources

Use these scripts only for legacy v1 flat JSON case files when the Detective MCP server is unavailable:

- **`scripts/board.py`** — Legacy board status and DOT graph export
- **`scripts/scoring.py`** — Legacy phase suggestion
- **`scripts/convergence.py`** — Legacy convergence status check
