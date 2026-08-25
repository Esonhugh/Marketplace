---
name: discuss-case
description: The assistant should use this when the user wants to discuss an existing Detective case, resolve a blocker, answer a targeted question, provide guidance/facts/theories, change scope, or choose between alternatives. It records guidance without running investigation. Do not use for new case creation (open-case), vague pre-case scoping (brainstorm), autonomous investigation (investigate), read-only status review (review-board), or closure (close-case).
---

# Discuss Case

Hold a structured case discussion and record useful guidance through Detective MCP tools. Follow `../references/detective-core-protocol.md` for canonical state, evidence labels, enums, StopHook status preservation, and handoffs.

<IMPORTANT name="user-guidance-boundary">
Discussion is for clarifying decisions, blockers, boundaries, and user-provided context. Ask one targeted question, record only useful guidance, and do not run investigation actions unless the user explicitly asks to switch back to investigation.
</IMPORTANT>

<IMPORTANT name="evidence-integrity">
Separate blackboard notes from verified graph state. User theories, guesses, preferences, and unverified memories are not evidence. Use `clue`, `verified`, and `confirmed` deliberately: only authoritative or corroborated user facts may become `evidence` with `status="confirmed"`.
</IMPORTANT>

<IMPORTANT name="goal-tool-scope-change">
When a SetGoal or equivalent goal tool is available, do not overwrite a valid active case goal during discussion. Update it only if the user changes scope, intent, completion criteria, or stop conditions. Session goals remain orchestration hints; MCP state remains canonical.
</IMPORTANT>

<IMPORTANT name="stop-fallback-status-preservation">
Discussion preserves the current Stop fallback marker status. Do not emit a new active marker merely for discussion. If the discussion ends with a user pause/stop request or a blocker waiting for user input, emit `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<pause|blocked>">`.
</IMPORTANT>

## Brief Before Asking

Read enough state to ask one targeted question:

- `detective_graph_overview(case_id="<case id>")`
- `detective_list_nodes(case_id="<case id>", limit=<reasonable limit>)`
- `detective_list_actions(case_id="<case id>")`
- `detective_blackboard_list(case_id="<case id>")`
- `detective_coverage_status(case_id="<case id>")`
- `detective_completion_gate(case_id="<case id>")`

Summarize only the relevant uncertainty, fork, or blocker.

## Recording User Input

Use the exact MCP tool that matches the input:

- Authoritative/confirmed user fact:
  - `detective_add_node(case_id="<case id>", type="evidence", content="<fact>", status="confirmed", confidence=<0..1>, source="user", tags=["user-provided"], created_by="assistant")`
- Believed but not fully confirmed user fact:
  - `detective_add_node(case_id="<case id>", type="clue", content="<signal>", status="verified", confidence=<0..1>, source="user", tags=["user-provided"], created_by="assistant")`
- User theory:
  - `detective_add_node(case_id="<case id>", type="hypothesis", content="<theory>", status="open", confidence=<0..1>, source="user", tags=["user-theory"], created_by="assistant")`
- Boundary or exclusion:
  - `detective_add_node(case_id="<case id>", type="constraint", content="<constraint>", status="open", confidence=1.0, source="user", tags=["boundary"], created_by="assistant")`
- Unverified note:
  - `detective_blackboard_add(case_id="<case id>", content="<note>", kind="note", tags=["unverified","user-provided"], created_by="assistant")`
- Relationship:
  - `detective_add_edge(case_id="<case id>", from_id="<node id>", to_id="<node id>", type="supports|contradicts|derives|requires|eliminates|related_to", confidence=<0..1>, rationale="<why>", created_by="assistant")`
- Follow-up work:
  - `detective_add_action(case_id="<case id>", description="<specific action>", assigned_role="assistant", priority=<0..1>, reason="<why this follows>")`
- Existing action update:
  - `detective_update_action(case_id="<case id>", action_id="<action id>", status="pending|active|blocked|done|cancelled", result="<discussion outcome>")`

When a blocker is resolved, hand off based on blocker type: proof/coverage/action gap → `investigate`; missing user decision/scope/approval → continue `discuss-case`; completion-ready → `close-case`; artifact-only → `review-board`.

## Response Format

```markdown
**Discussion point**: <uncertainty or fork>
**What I recorded**: <node/action ids or "nothing yet">
**Goal tool**: <unchanged/updated/unavailable>
**Stop fallback**: <preserved | inactive marker emitted with reason>
**Current decision needed**: <one question only>
```
