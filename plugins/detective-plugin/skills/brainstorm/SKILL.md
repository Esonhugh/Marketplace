---
name: brainstorm
description: The assistant should use this when the user has a vague concern, hunch, symptom, unknown failure, or asks what to investigate before any Detective case exists. It produces a read-only, approval-ready brief. Do not use when the user explicitly asks to create/open a case (use open-case), continue an existing case (use investigate), review status (use review-board), resolve a known blocker with user guidance (use discuss-case), or close/finalize findings (use close-case).
---

# Brainstorm — Pre-Case Exploration

Turn an unclear concern into a concise case brief. Follow the shared protocol in `../references/detective-core-protocol.md` for enums, evidence labels, handoffs, and orchestration boundaries.

<HARD_GATE_PRE_APPROVAL_NO_MUTATION>
Brainstorm is pre-approval only. Do not call `detective_open_case`, `detective_add_node`, `detective_add_edge`, `detective_add_intent`, `detective_add_action`, or any other case-mutating MCP tool until the user explicitly approves the brief and asks to proceed. Read-only code/file/log inspection is allowed when it helps frame the problem.
</HARD_GATE_PRE_APPROVAL_NO_MUTATION>

<HARD_GATE_EXPLICIT_OPEN_APPROVAL>
User approval must be explicit and current-turn clear, for example "open it", "proceed", or "create the case". Ambiguous interest, agreement with the brief, or continued brainstorming is not permission to mutate Detective MCP state.
</HARD_GATE_EXPLICIT_OPEN_APPROVAL>

<IMPORTANT_GOAL_AND_STOP_TIMING>
Do not call SetGoal or emit `<DETECTIVE-STOP-FALLBACK ...>` markers during unapproved brainstorming. After approval, hand off to `/detective:open-case` when available; open-case handles durable MCP creation, SetGoal, and fallback markers.
</IMPORTANT_GOAL_AND_STOP_TIMING>

<HARD_GATE_NO_STOP_FALLBACK_BEFORE_APPROVAL>
Do not emit `<DETECTIVE-STOP-FALLBACK ...>` markers during brainstorm pre-approval. Stop fallback activation is allowed only after a durable MCP case exists and only as a fallback when no SetGoal or equivalent goal tool is available.
</HARD_GATE_NO_STOP_FALLBACK_BEFORE_APPROVAL>

## Workflow

1. Restate the symptom, suspected area, and why it matters.
2. Do read-only pre-work when it can answer obvious questions without mutating case state.
3. Ask exactly one clarifying question at a time; prefer concrete choices.
4. Classify inputs using current protocol terms: observation, clue, hypothesis, constraint, success criterion, open question.
5. Agree on scope, out-of-scope boundaries, budget, and checkpoint cadence.
6. Produce an approval-ready brief.
7. Ask whether to open it; on explicit approval, invoke `detective:open-case` or directly follow that skill's MCP procedure if skills are unavailable.

## Case Brief Template

```markdown
## Case Brief: <short title>

**Crime Scene**: <observable problem>
**Investigation Intent**: <what the user wants to learn or decide>
**Success Criteria**: <what counts as solved>
**Scope**: <in scope / out of scope>
**Budget**: <max actions or time box; checkpoint cadence>

**Initial Observations**:
- <known fact or symptom>

**Initial Hypotheses**:
- <hypothesis> — confidence: <low|medium|high>; basis: <why>

**Initial Clues**:
- <partially supported signal and source>

**Constraints**:
- <hard boundary or exclusion>

**Open Questions**:
- <uncertainty that should drive early actions>

**Suggested First Action**: <first MCP action after case creation>
```

End by asking one question: "Does this brief capture the case? If yes, should I open it with `/detective:open-case` now?"
