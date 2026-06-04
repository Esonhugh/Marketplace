---
name: investigate
description: This skill should be used when the user asks to "investigate", "continue the investigation", "run the detective loop", "next investigation step", or wants to execute the Scan-Evolve-Focus-Act-File cycle on an active case. Runs the core investigation loop with periodic checkpoints.
---

# Investigate — MCP-Backed Detective Loop

Execute the investigation cycle on an active MCP-backed case. Prefer Detective MCP tools over direct JSON edits or legacy scripts.

## Prerequisites

An active case must exist under `.detective/cases/`. If the MCP server is unavailable, explain that v2.1 investigation requires the detective MCP server and ask the user to check `/mcp`.

## Loop

1. Call `detective_graph_overview`.
2. List active hypotheses, open questions, and recent evidence with `detective_list_nodes`.
3. Generate candidate actions and call `detective_score_candidate_actions`.
4. In `full_auto`, dispatch specialist agents for independent actions; in `checkpoint`, run up to the checkpoint interval; in `manual`, ask the user before acting.
5. Require all findings to be written through MCP tools.
6. Call `detective_convergence_status` and `detective_deadlock_status`.
7. Export Markdown and Mermaid with `detective_export_markdown` and `detective_export_mermaid` after meaningful graph changes.
8. Stop on convergence, deadlock, budget exhaustion, or user intervention.

## Legacy script fallback

This section is deprecated. Use it only for legacy v1 flat JSON case files when the Detective MCP server is unavailable. It is not the workflow for Detective v2/v2.1 cases.

For v2/v2.1 cases:
- Stop if required MCP tools are unavailable and ask the user to check `/mcp`.
- Record findings, graph changes, convergence checks, and exports through Detective MCP tools.
- Do not use legacy scripts to mutate case state.

### Legacy v1 read-only inspection

For legacy v1 flat case files, the old scripts can inspect status when MCP is unavailable:

```bash
python $PLUGIN_ROOT/scripts/board.py status .detective/cases/<case-id>.json
python $PLUGIN_ROOT/scripts/scoring.py suggest-phase .detective/cases/<case-id>.json
python $PLUGIN_ROOT/scripts/convergence.py .detective/cases/<case-id>.json
```

Use the output to assess:
- Which Fragments are isolated or unsupported.
- Which Threads are broken or contradictory.
- Which Hypotheses remain active or eliminated.
- Whether the legacy case appears converged.

### Legacy v1 reasoning cycle

When reviewing a legacy v1 flat case without MCP, treat the old Scan → Evolve → Focus → Act → File loop as a reasoning model only:

1. **Scan**: inspect the board status and current phase.
2. **Evolve**: identify constraints or maturity changes that would matter.
3. **Focus**: generate candidate actions and score them conceptually, or with the legacy scorer for v1 files only.
4. **Act**: execute the selected investigation action with available tools.
5. **File**: for v2/v2.1, write findings through MCP tools; for legacy v1 fallback, summarize findings without mutating the flat case file.

Legacy mutation commands such as fragment creation, thread creation, maturity changes, and propagation are deprecated. Do not use them for v2/v2.1 cases.

### Checkpoints and termination

For legacy v1 fallback, stop when convergence is reported, the user asks to pause, the action budget is exhausted, or discussion is needed. For v2/v2.1, use `detective_convergence_status`, `detective_deadlock_status`, and MCP exports instead of script-based checkpointing.

### Additional resources

These scripts are legacy v1 fallback references only:
- **`scripts/board.py`** — Legacy board inspection and deprecated mutation helpers
- **`scripts/scoring.py`** — Legacy phase suggestion and scoring helpers
- **`scripts/convergence.py`** — Legacy convergence inspection
