---
name: review-board
description: The assistant should use this when the user asks to show, summarize, audit, export, or review the current Detective board/status/progress/evidence graph/blockers without changing case state. It is read-only by default. Do not use for new cases (open-case), pre-case brainstorming (brainstorm), autonomous next steps (investigate), guidance/blocker conversation needing writes (discuss-case), or closure (close-case).
---

# Review Board

Display current Detective MCP case state. Follow `../references/detective-core-protocol.md` for canonical state, enums, proof semantics, evidence lifecycle, and export policy.

<HARD_GATE_READ_ONLY_BOUNDARY>
Default to reads only. Do not add, update, close, or otherwise mutate cases during board review. Exports are the only allowed write-like side effect, and only when the user asks for files/artifacts or the review will be handed off.
</HARD_GATE_READ_ONLY_BOUNDARY>

<IMPORTANT_COMPLETION_GATE_DEFAULT>
Use `detective_completion_gate(case_id="<case id>")` as the default read-only proof readiness check. Do not call `detective_evaluate_proof` during routine review; call it only when the user requests a durable formal proof snapshot or a closure/reporting workflow needs one.
</IMPORTANT_COMPLETION_GATE_DEFAULT>

<IMPORTANT_EVIDENCE_INTEGRITY>
Present blackboard content as unverified scratch, not verified graph evidence. Clearly label clues, confirmed evidence, direct `supports` edges, contradictions, caveats, proof-gate blockers, and coverage gaps.
</IMPORTANT_EVIDENCE_INTEGRITY>

<IMPORTANT_GOAL_TOOL_REVIEW_BOUNDARY>
When a SetGoal or equivalent goal tool is available, do not overwrite a valid active case goal during review. Update it only if the user explicitly changes investigation scope, intent, completion criteria, or stop conditions.
</IMPORTANT_GOAL_TOOL_REVIEW_BOUNDARY>

<IMPORTANT_STOP_FALLBACK_STATUS_PRESERVATION>
Board review preserves the current Stop fallback marker status. Do not emit a new active marker merely for review. If review shows completion is allowed, the case is blocked waiting for user input, budget is exhausted, or the user asked to pause/stop after the review, emit `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<complete|blocked|budget-exhausted|pause>">`.
</IMPORTANT_STOP_FALLBACK_STATUS_PRESERVATION>

## Required Reads

- `detective_case_status(case_id="<case id>")`
- `detective_graph_overview(case_id="<case id>")`
- `detective_list_nodes(case_id="<case id>", limit=<reasonable limit>)`
- `detective_list_edges(case_id="<case id>")`
- `detective_list_actions(case_id="<case id>")`
- `detective_blackboard_list(case_id="<case id>")`
- `detective_coverage_status(case_id="<case id>")`
- `detective_completion_gate(case_id="<case id>")`

Optional only for durable proof snapshots:

- `detective_evaluate_proof(case_id="<case id>", summary="<current board review>")`

## Optional Exports

Only export when the user asks for files/artifacts or the review will be handed off:

- `detective_export_markdown(case_id="<case id>")`
- `detective_export_mermaid(case_id="<case id>", diagram="full", focus_node_id=null)`
- Optional focused graph: `detective_export_mermaid(case_id="<case id>", diagram="hypothesis-chain", focus_node_id="<node id>")`

## Structured Output

```markdown
**Case**: <case_id> — <title/status>
**OODA phase**: <phase>
**Intent**: <intent if available>
**Goal tool**: <unchanged/updated/unavailable>
**Stop fallback**: <preserved | inactive marker emitted with reason>
**Leading hypotheses**:
- <hypothesis> — confidence, supporting/contradicting evidence
**Evidence chains**:
- <confirmed evidence> → supports → <hypothesis>
**Contradictions / caveats**:
- <items>
**Open questions**:
- <items>
**Coverage**:
- Covered: <areas>
- Planned: <areas>
- Blocked/gaps: <areas>
**Actions**:
- Active: <items>
- Done recently: <items>
- Blocked: <items>
**Completion gate**: <allowed/blocked and reason>
**Suggested next move**: <investigate | discuss-case | close-case | pause>
**Exports**: <paths, or "not requested">
```
