---
name: investigate
description: The assistant should use this when the user asks to continue, resume, advance, work, or run the next step for an existing Detective case id. It autonomously drives MCP OODA cycles. Do not use to create a new case (use open-case), pre-scope a vague concern (use brainstorm), only show status/exports (use review-board), ask/record user guidance without investigation (use discuss-case), or finalize closure (use close-case).
---

# Investigate

Run Detective OODA cycles through MCP tools only. Follow `../references/detective-core-protocol.md` for exact enums, proof semantics, evidence lifecycle, SetGoal preference, StopHook markers, stop conditions, and handoffs.

<HARD_GATE name="case-state-safety">
Use Detective MCP as the only source of case truth. Never edit `.detective/` files directly, never bypass MCP lifecycle tools, and never treat blackboard notes as verified graph evidence.
</HARD_GATE>

<HARD_GATE name="ooda-phase-discipline">
Every investigation step must pass through observe, orient, decide, act, and review in order, recording each transition with `detective_transition_phase`. On mid-cycle resume, read current phase/actions, close or repair interrupted work, transition to the next legal phase, and continue; do not restart the case or skip phase records.
</HARD_GATE>

<IMPORTANT name="goal-tool-adoption">
When a SetGoal or equivalent goal tool is available, inspect the active session goal before work. Adopt it if it matches the case id, intent, completion criteria, and autonomous OODA instruction. If missing or clearly for another case, set a concise goal from current MCP intent and completion criteria. Do not overwrite a valid active goal merely to rephrase it.
</IMPORTANT>

<HARD_GATE name="stop-fallback-marker-protocol">
Prefer SetGoal or equivalent for autonomous continuation. Only when no goal tool is available, ensure the transcript contains `<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">` before self-driven work. The marker activates only the statically registered inert StopHook fallback; it is not MCP state and must not be written to `.detective/` files. Before stopping with fallback active, emit `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<pause|blocked|budget-exhausted|complete|closed>">`.
</HARD_GATE>

<HARD_GATE name="subagent-delegation">
Delegate only bounded, independent investigation work. Every subagent dispatch must state the Detective case id, current OODA phase and action id, exact scope or target nodes, allowed tools and read/write boundaries, required Detective MCP writes, expected return format, and stop conditions. Subagents must obey the same evidence, state, scope, and closure gates as the coordinator: they must never edit `.detective/` directly, expand scope, force-close a case, treat blackboard notes as proof, or spawn further agents unless the dispatch explicitly permits it. The coordinator must validate returned evidence and MCP state before marking the parent action done or advancing the completion gate.
</HARD_GATE>

## Start-of-Turn Reads

Call before deciding work:

- `detective_case_status(case_id="<case id>")`
- `detective_graph_overview(case_id="<case id>")`
- `detective_list_nodes(case_id="<case id>", limit=<reasonable limit>)`
- `detective_list_edges(case_id="<case id>")`
- `detective_list_actions(case_id="<case id>")`
- `detective_blackboard_list(case_id="<case id>")`
- `detective_coverage_status(case_id="<case id>")`
- `detective_list_intents(case_id="<case id>")` when needed for goal adoption.

## Autonomous OODA Workflow

Continue cycles until a standard stop condition applies. Do not ask routine mid-loop questions when current state permits a legal high-value next action.

1. **Observe**
   - `detective_transition_phase(case_id="<case id>", phase="observe", reason="collect current facts")`
   - Gather facts using read-only tools, specialist agents, or user data.
   - Verified facts → `detective_add_node(..., type="evidence"|"observation")` with accurate `source` and status.
   - Partial signals → `type="clue"`; scratch/speculation → `detective_blackboard_add(...)`.
2. **Orient**
   - `detective_transition_phase(case_id="<case id>", phase="orient", reason="relate evidence and hypotheses")`
   - Add/update edges/statuses with exact edge enums; promote blackboard only when a graph node is warranted, not as proof.
3. **Decide**
   - `detective_transition_phase(case_id="<case id>", phase="decide", reason="select next action")`
   - Choose the highest-value legal action and create exactly that item:
     `detective_add_action(case_id="<case id>", description="<specific action>", assigned_role="<assistant|agent name>", priority=<0..1>, reason="<why highest value>")`.
4. **Act**
   - `detective_transition_phase(case_id="<case id>", phase="act", reason="execute selected action <action_id>")`
   - Execute the action; when delegating, apply every field and boundary in the subagent-delegation hard gate.
   - Record evidence, contradictions, resolved/rejected questions, rejected/resolved alternatives, or blackboard notes through MCP.
5. **Review**
   - `detective_transition_phase(case_id="<case id>", phase="review", reason="record results and check readiness")`
   - Close action lifecycle: `detective_update_action(..., status="done|blocked|cancelled", result="<result>")`.
   - Add checkpoint: `detective_add_checkpoint(case_id="<case id>", summary="<what changed>", action_id="<action id>", created_by="assistant")`.
   - Update existing coverage with `detective_coverage_update(case_id="<case id>", coverage_id="<existing id>", ...)`. Add coverage only for a genuinely new area; never create a second item with the same area to represent progress.
   - Resolve or reject the original open `question` nodes with `detective_update_node`; do not add a separate answer question while leaving the original question open.
   - Re-read actions, questions, and coverage, then check readiness with read-only `detective_completion_gate(case_id="<case id>")`. Call `detective_evaluate_proof` only after the read-only gate is allowed or when a durable failing snapshot is explicitly required. A failed gate is feedback to repair existing state within budget, not a reason to duplicate coverage/questions or repeatedly evaluate proof.

## Proof Alignment

Before suggesting closure, ensure exactly one confirmed hypothesis, at least one confirmed evidence node with a direct `supports` edge to it, alternatives rejected/stale/resolved, questions resolved/rejected, actions done/cancelled, and coverage complete.

Do not use an absent, unreadable, or unexamined source as a `contradicts`/`eliminates` edge or as grounds to lower an alternative hypothesis. Missing expected evidence proves only the source/coverage limitation unless independent evidence makes the hypothesis predict an observation that did not occur.

<HARD_GATE name="autonomy-stop-conditions">
Stop before another action only when closure is allowed, user intervention is required, no legal action remains, budget/timebox/step count is exhausted, critical coverage needs approval, requested step count is reached, handoff is required, or the user asks to pause. Report the reason and deactivate fallback if active.
</HARD_GATE>

Export with `detective_export_markdown` and `detective_export_mermaid(..., diagram="full", focus_node_id=null)` only after meaningful graph changes or when requested.

## Response Format

```markdown
**Phase completed**: review
**Action**: <description and status>
**OODA cycles run**: <n and stop reason>
**Goal tool**: <adopted/set/unavailable/no change>
**Stop fallback**: <inactive due to goal tool | active marker emitted | inactive marker emitted with reason | unchanged>
**New evidence / graph changes**: <bullets>
**Coverage**: <statuses>
**Proof gate**: <allowed/blocked and key reason>
**Next recommended action**: <specific next action, handoff, or ask>
```
