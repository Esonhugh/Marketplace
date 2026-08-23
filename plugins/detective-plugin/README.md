# Detective v0.4 — OODA-Native Investigation MCP

Detective is a Claude Code plugin for structured investigations. v0.4 is a breaking release: the public surface is one MCP API, one project-local JSON case model, and one OODA-native lifecycle. Legacy v1 scripts, migration APIs, scheduler-next-action APIs, and separate convergence/deadlock APIs are not part of this release.

## Model

A case is stored at `.detective/cases/<case-id>/case.json` and is mutated only through MCP tools. The case contains:

- `nodes`: observations, clues, evidence, hypotheses, constraints, conclusions, questions, and tasks.
- `edges`: directed reasoning links: `supports`, `contradicts`, `derives`, `requires`, `eliminates`, `related_to`.
- `ooda`: current phase plus investigation intents.
- `blackboard`: scratch notes that can be promoted to graph nodes.
- `actions`: planned/active/done investigation work.
- `coverage`: investigation areas and completion status.
- `proofs`, `checkpoints`, `events`, and `closure`: audit trail and completion gate state.

The lifecycle is OODA: Observe → Orient → Decide → Act → Review. Record phase changes with `detective_transition_phase`, track goals with intents, execute work as actions, and close only after `detective_completion_gate` allows it or the user explicitly forces closure. Investigation skills are designed to self-drive OODA loops until the completion gate passes or an explicit stop condition applies.

When a SetGoal or equivalent goal tool is available in the harness, Detective skills may use it for session orchestration: after case creation, the goal should mention the case id, intent, completion criteria, and autonomous OODA advancement. This never replaces `detective_open_case` or MCP case state; `.detective/cases/<case-id>/case.json` remains canonical and is mutated only through MCP tools.

## StopHook fallback

SetGoal or an equivalent goal-driven continuation mechanism is preferred for keeping active investigations moving. The plugin also ships a prompt-based Stop hook as a safety fallback, but the static registration is inert by default: the hook immediately approves stopping unless the transcript contains an explicit activation marker.

Dynamic activation is transcript-driven, not filesystem-driven. Skills must not edit `.detective/` files or hook files to control the fallback. When no SetGoal-equivalent tool is available, `/detective:open-case` or `/detective:investigate` may emit a concise visible marker after a durable MCP case exists:

```xml
<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">
```

The matching deactivation marker is emitted on user pause/stop, blocked state, budget/timebox/step exhaustion, completion, or close:

```xml
<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<pause|blocked|budget-exhausted|complete|closed>">
```

For each case id, the latest marker wins. A case is fallback-active only when its latest marker is `status="active"`; a later `status="inactive"` for that case disengages it. The hook must not infer activation merely from an open or active Detective case. Brainstorming never emits activation before user approval and durable MCP case creation. Review and discussion preserve current status except when they identify a stop/deactivation condition.

When marker-active, the Stop hook still approves stopping when the case is closed or completion gate passed, the user asks to stop or pause, the assistant is waiting for a user-only decision, the case is blocked or no legal action remains, budget or `max_actions` is exhausted, a goal mechanism is active/available, non-Detective tasks/tests are complete, or repeated StopHook blocking/cycling is visible. It blocks only when the marked case is unfinished, no goal mechanism is available, and a concrete legal useful next OODA action remains.

Claude Code loads plugin hooks when a session starts. This marker protocol does not truly hot-add or hot-remove hooks; it only makes the already registered Stop hook fail open or engage based on transcript context. True hook loading changes require restarting Claude Code and are not attempted by Detective.

## Exact public MCP tools

- `detective_open_case`
- `detective_load_case`
- `detective_graph_overview`
- `detective_case_status`
- `detective_transition_phase`
- `detective_add_intent`
- `detective_list_intents`
- `detective_add_node`
- `detective_update_node`
- `detective_delete_node`
- `detective_get_node`
- `detective_list_nodes`
- `detective_search_nodes`
- `detective_add_edge`
- `detective_get_edge`
- `detective_update_edge`
- `detective_delete_edge`
- `detective_list_edges`
- `detective_neighbors`
- `detective_shortest_path`
- `detective_export_markdown`
- `detective_export_mermaid`
- `detective_add_action`
- `detective_update_action`
- `detective_list_actions`
- `detective_add_checkpoint`
- `detective_blackboard_add`
- `detective_blackboard_list`
- `detective_blackboard_update`
- `detective_blackboard_promote`
- `detective_coverage_add`
- `detective_coverage_update`
- `detective_coverage_status`
- `detective_evaluate_proof`
- `detective_completion_gate`
- `detective_close_case`
- `detective_list_events`

## Removed in v0.4

- Legacy public APIs are intentionally not restored.

Completion requires exactly one `hypothesis` node with status `confirmed` and direct `supports` evidence from a `confirmed` `evidence` node, no open alternatives/questions/actions, and complete coverage.
- Legacy v1 scripts and helper modules.
- Load-time schema migration. v0.4 creates and accepts schema `4.0` cases only.

## Usage

```bash
/detective:brainstorm
/detective:open-case "Investigate the root cause of this regression"
/detective:investigate
/detective:review-board
/detective:discuss-case
/detective:close-case
```

Skills and agents must use MCP tools and must not edit `.detective/` files directly.

## Storage and exports

Canonical state:

```text
.detective/cases/<case-id>/case.json
.detective/cases/<case-id>/events.jsonl
```

Generated projections:

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
```

JSON is the only canonical state. Markdown and Mermaid are regenerated views.
