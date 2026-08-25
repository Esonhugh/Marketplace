---
name: open-case
description: The assistant should use this when the user explicitly asks to open/create/start a Detective MCP case, begin an OODA investigation, or approves a brainstorm brief. It creates durable case state. Do not use for vague pre-case scoping without approval (use brainstorm), existing-case continuation (use investigate), status review (use review-board), blocker discussion (use discuss-case), or finalization (use close-case).
---

# Open Case

Create a Detective MCP-backed case. Follow `../references/detective-core-protocol.md` for canonical MCP-only state, enums, evidence lifecycle, SetGoal preference, StopHook fallback, and handoffs.

<HARD_GATE name="case-state-safety">
All case state creation and updates must go through Detective MCP tools. Never create, edit, rename, delete, or infer truth from `.detective/` files as a substitute for MCP state. Preserve exact MCP tool names, enums, parameters, and signatures.
</HARD_GATE>

<IMPORTANT name="goal-tool-boundary">
When a SetGoal or equivalent goal tool is available, use it only for harness/session orchestration after `detective_open_case` returns the case id. It does not create durable Detective case state and must not be treated as MCP truth.
</IMPORTANT>

<HARD_GATE name="stop-fallback-marker-protocol">
Prefer SetGoal or an equivalent goal tool. Only when no goal tool is available, emit exactly once after `detective_open_case` returns: `<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">`. This only activates the statically registered inert StopHook fallback and must not be written to `.detective/` files.
</HARD_GATE>

## Required Inputs

Ask one concise question at a time until you have title, description/crime scene, intent, budget, and scope.

## Budget Mapping

Pass budget via `detective_open_case(..., config={...})`:

- `max_actions` or "N steps" → `{"max_actions": N}`.
- Checkpoint cadence → add `"checkpoint_interval": <positive integer>`.
- Time box → add `"timebox": "<verbatim>"`.
- If absent, use `{"max_actions": 8, "checkpoint_interval": 3}` and state the default.
- Seed coverage after opening with `detective_coverage_add`; do not put coverage in config.

## Exact Workflow

1. Create durable case:
   - `detective_open_case(title="<title>", description="<description>", case_id=null, config=<budget_config>)`
   - Use `case_id` only if the user provided one; otherwise let MCP generate numbering/slug.
2. Set orchestration only after durable case creation:
   - If SetGoal or equivalent exists, set a concise goal with returned case id, intent, completion criteria, autonomous OODA instruction, and stop conditions.
   - If unavailable, emit `<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">`.
3. Enter Observe:
   - `detective_transition_phase(case_id="<case id>", phase="observe", reason="case opened")`
4. Record intent:
   - `detective_add_intent(case_id="<case id>", intent="<user intent>", phase="observe", created_by="assistant", metadata={"source":"open-case"})`
5. Add an optional goal node only for graph reasoning or explicit success criteria:
   - `detective_add_node(case_id="<case id>", type="question", content="Goal: <success criteria>", status="open", confidence=1.0, source="user", tags=["goal"], created_by="assistant", metadata={"is_goal": true})`
6. Seed graph from the brief:
   - Crime scene → `type="observation"`, `source="user"`, `tags=["crime-scene"]`.
   - Verified facts → `type="evidence"`; partial signals → `type="clue"`; theories → `type="hypothesis"`; boundaries → `type="constraint"`; uncertainties → `type="question"`.
7. Link seed nodes where useful with `detective_add_edge(..., type="supports|contradicts|derives|requires|eliminates|related_to", ...)`.
8. Put uncertain scratch ideas on blackboard: `detective_blackboard_add(case_id="<case id>", content="<uncertain note>", kind="note", tags=["unverified"], created_by="assistant")`.
9. Seed coverage with `detective_coverage_add(case_id="<case id>", area="<area>", status="planned", notes="seeded from open-case scope")`; use `"initial triage"` if no areas are known.
10. Report case id, phase, intent, budget, seeded counts, coverage, goal-tool status, fallback status, and suggested `/detective:investigate` next step.

## Output Format

```markdown
**Case opened**: <case_id>
**Phase**: observe
**Intent**: <intent>
**Budget**: <config summary>
**Goal tool**: <set/unavailable; MCP case remains canonical>
**Stop fallback**: <inactive because goal tool set | activated with marker because no goal tool is available>
**Seeded**: <counts>
**Coverage**: <areas>
**Suggested next step**: Run `/detective:investigate` to execute autonomous OODA cycles.
```
