---
name: close-case
description: The assistant should use this when the user asks to close, finalize, force-close, wrap up with a final conclusion, or produce final Detective case findings. It closes only after proof readiness or explicit force approval. Do not use for status-only review (review-board), further investigation (investigate), blocker discussion (discuss-case), new case creation (open-case), or pre-case scoping (brainstorm).
---

# Close Case

Close a Detective MCP-backed case only through MCP tools. Follow `../references/detective-core-protocol.md` for proof completion semantics, canonical state, StopHook deactivation, handoffs, and export policy.

<HARD_GATE_CLOSURE_AUTHORIZATION>
Normal closure requires `detective_completion_gate` approval and a final summary naming conclusion, confidence, key evidence chain, completed coverage, and unresolved caveats. If the gate is blocked, do not close; present blockers and offer continue, discuss, or force-close options.
</HARD_GATE_CLOSURE_AUTHORIZATION>

<HARD_GATE_FORCE_CLOSE_APPROVAL>
`force=true` requires explicit user approval for a partial or forced close in the current conversation. Include the force reason and unresolved caveats in the summary; never infer force approval from frustration, silence, or a generic request to wrap up.
</HARD_GATE_FORCE_CLOSE_APPROVAL>

<IMPORTANT_PROOF_LIFECYCLE_ALIGNMENT>
Before normal closure, verify exactly one confirmed hypothesis, at least one confirmed evidence node with a direct `supports` edge to it, questions and alternatives resolved/rejected/stale, actions done/cancelled, and coverage complete. Use `detective_completion_gate` as the readiness authority; use `detective_evaluate_proof` only when preserving a durable final proof snapshot.
</IMPORTANT_PROOF_LIFECYCLE_ALIGNMENT>

<IMPORTANT_GOAL_COMPLETION_ALIGNMENT>
When a SetGoal or equivalent goal tool is available, treat `detective_completion_gate` approval as the goal-completion gate. Session goals are orchestration hints and do not replace MCP closure state.
</IMPORTANT_GOAL_COMPLETION_ALIGNMENT>

<HARD_GATE_STOP_FALLBACK_DEACTIVATION_ON_CLOSE>
When closure is completed, blocked waiting for user force-close approval, or paused by user request, emit `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<closed|blocked|pause>">`. This only disengages the transcript-activated fallback and must not be written to `.detective/` files.
</HARD_GATE_STOP_FALLBACK_DEACTIVATION_ON_CLOSE>

## Required Inputs

Obtain or draft `case_id`, `summary`, `approved_by` (user role/name if provided, else `assistant` after gate approval), and `force=false` unless explicitly approved.

## Exact Workflow

1. Read final state:
   - `detective_case_status(case_id="<case id>")`
   - `detective_graph_overview(case_id="<case id>")`
   - `detective_coverage_status(case_id="<case id>")`
   - `detective_completion_gate(case_id="<case id>")`
2. If a durable final proof snapshot is requested or needed for final reporting, call:
   - `detective_evaluate_proof(case_id="<case id>", summary="<draft final summary>")`
3. If the completion gate is blocked, present blockers and route:
   - proof/coverage/action gaps → offer `/detective:investigate`;
   - missing user decision/scope/caveat approval → offer `/detective:discuss-case`;
   - explicit partial-finalization request → ask for force-close approval.
4. For normal closure:
   - `detective_close_case(case_id="<case id>", summary="<final summary>", approved_by="<approver>", force=false)`
5. For explicit partial/forced closure:
   - `detective_close_case(case_id="<case id>", summary="<summary including caveats and force reason>", approved_by="<approver>", force=true)`
6. After successful close, export:
   - `detective_export_markdown(case_id="<case id>")`
   - `detective_export_mermaid(case_id="<case id>", diagram="full", focus_node_id=null)`
   - Optional focused diagram only if useful: `detective_export_mermaid(case_id="<case id>", diagram="hypothesis-chain", focus_node_id="<node id>")`
7. Emit inactive marker with reason `closed`, `blocked`, or `pause` as applicable:
   - `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="closed">`
   - `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="blocked">`

## Final Summary Template

```markdown
Conclusion: <what happened / answer>
Confidence: <low|medium|high> — <why>
Key evidence chain:
- <confirmed evidence> → supports → <confirmed hypothesis/conclusion>
Coverage completed:
- <areas>
Unresolved caveats:
- <caveat or "none known">
Closure type: <normal|forced partial>
```

## Response Format

```markdown
**Case closed**: <case_id>
**Closure type**: <normal|forced partial>
**Conclusion**: <one paragraph>
**Confidence**: <level and reason>
**Caveats**: <bullets>
**Goal completion**: <completion gate passed / forced with explicit approval>
**Stop fallback**: <inactive marker emitted with reason>
**Exports**:
- Markdown: <path from MCP>
- Mermaid: <path from MCP>
```
