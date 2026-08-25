# Detective Core Protocol

## TOC
1. Canonical state
2. Exact enums
3. Evidence lifecycle
4. Proof completion
5. Orchestration and StopHook
6. Autonomous OODA
7. Subagent delegation
8. Stop conditions
9. Cross-skill handoff
10. Export policy

## 1. Canonical state

- Detective MCP state is the only durable case truth.
- Never create, edit, rename, delete, or infer truth from `.detective/` files as a substitute for MCP tools.
- Session goals, transcript markers, exports, and summaries are orchestration/artifacts, not canonical state.
- Use exact current MCP tool names and signatures from the active server.

## 2. Exact enums

Node types: `observation`, `clue`, `evidence`, `hypothesis`, `constraint`, `conclusion`, `question`, `task`.

Node statuses: `open`, `verified`, `rejected`, `stale`, `resolved`, `confirmed`.

Edge types: `supports`, `contradicts`, `derives`, `requires`, `eliminates`, `related_to`.

Sources: `user`, `agent`, `tool`, `file`, `web`, `mcp`, `system`.

OODA phases: `observe`, `orient`, `decide`, `act`, `review`.

Action statuses: `pending`, `active`, `blocked`, `done`, `cancelled`.

Blackboard statuses: `draft`, `active`, `promoted`, `archived`.

Coverage statuses: `unknown`, `planned`, `partial`, `complete`, `blocked`.

Case statuses: `open`, `paused`, `closed`.

## 3. Evidence lifecycle

- Blackboard: scratch, speculation, partial memory, planning notes. Not proof.
- `clue`: partially supported signal that needs verification.
- `observation`: observed condition or symptom; may be user/file/tool sourced.
- `evidence`: verified fact with source; use `status="confirmed"` only when directly confirmed.
- `hypothesis`: candidate explanation. Confirm exactly one only at proof time.
- User facts:
  - Unverified user memory or theory → blackboard or `hypothesis`.
  - User-provided fact believed but not externally checked → `clue` or `evidence` with `status="open"`/`verified` as appropriate.
  - Explicitly verified or authoritative user fact → `evidence`, `source="user"`, `status="confirmed"` when strong enough.
- Missing, inaccessible, or unexamined expected evidence may establish a blocker or coverage gap, but it does not contradict, eliminate, weaken, or reduce the confidence of a causal hypothesis. Record the missing source as an observation/constraint and keep affected hypotheses unresolved unless independent contrary evidence exists.
- Promotion from blackboard creates a graph node but does not make it verified; choose node type/status/source conservatively.

## 4. Proof completion semantics

A case is complete only when all are true:

1. Exactly one `hypothesis` has `status="confirmed"`.
2. At least one `evidence` node has `status="confirmed"` and a direct `supports` edge to that confirmed hypothesis.
3. Active alternative hypotheses above the elimination threshold are `rejected`, `stale`, or `resolved`, or have an `eliminates`/`contradicts` rationale recorded as appropriate.
4. Open `question` nodes are `resolved` or `rejected`.
5. All actions are `done` or `cancelled`; blockers are represented and handed off if not closed.
6. Coverage is complete for in-scope areas.

Use `detective_completion_gate(case_id=...)` as the read-only default readiness check. Use `detective_evaluate_proof(case_id=..., summary=...)` only when a durable formal proof snapshot is requested or needed before closure/reporting.

## 5. Orchestration and StopHook

- Prefer SetGoal or an equivalent goal tool for session orchestration after durable MCP case creation.
- SetGoal must include case id, intent, completion criteria, autonomous OODA instruction, and stop conditions.
- Do not treat SetGoal as MCP state.
- Dynamic marker-activated StopHook fallback is inert until a marker appears in the visible transcript.
- If no goal tool exists, activate once per case with:
  `<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">`
- Deactivate before stopping on pause/block/budget/complete/closed with:
  `<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<pause|blocked|budget-exhausted|complete|closed>">`
- Latest marker wins for the same case id. Never write markers to `.detective/` files.

## 6. Autonomous OODA

For investigation, loop observe → orient → decide → act → review and record every transition with `detective_transition_phase`. Mid-cycle resume is allowed: read current case/actions/phase, close or repair the interrupted action, transition to the next legal phase, and continue without restarting the case.

Cycle duties:

- Observe: read current state and collect facts; add evidence/observations/clues or blackboard notes.
- Orient: relate nodes; add/update edges and statuses.
- Decide: choose the highest-value legal next action; add exactly that action.
- Act: execute the action using tools/agents and write findings through MCP.
- Review: update action status, add checkpoint, update the existing coverage item by id (do not add a duplicate area), resolve/reject the original open question nodes by id, then check completion gate.

Do not ask routine mid-loop questions when a legal high-value action can be chosen from state.

## 7. Subagent delegation

<HARD_GATE name="subagent-delegation">
Delegate only bounded, independent work. Every dispatch must include the Detective case id, OODA phase and action id, scope or target nodes, allowed tools and read/write boundaries, required MCP writes, expected return format, and stop conditions. Subagents inherit the coordinator's evidence, state, scope, and closure constraints. They must never edit `.detective/` directly, expand scope, force-close, convert scratch into proof, or spawn further agents unless explicitly allowed. The coordinator validates returned evidence and MCP state before completing the parent action.
</HARD_GATE>

## 8. Standard stop conditions

Stop only when closure is allowed, explicit user pause/stop, user input is required, no legal action remains, budget/step limit/timebox is exhausted, critical coverage requires scope approval, or a handoff is required by blocker type.

## 9. Cross-skill handoff matrix

- Vague concern/no approved case → `brainstorm`.
- Approved brief or explicit new case → `open-case`.
- Existing case needs work or resume → `investigate`.
- User guidance, blocker resolution, scope decision → `discuss-case`.
- Status/progress/graph/exposure without mutation → `review-board`.
- Completion gate passed or user requests forced finalization → `close-case`.
- Gate blocked by proof/coverage/action gaps → `investigate`.
- Gate blocked by missing user decision/scope/caveat approval → `discuss-case`.
- User asks for artifacts only → `review-board` export policy.

## 10. Export policy

- Exports are artifacts, not state.
- `review-board` exports only when requested or required for handoff.
- `investigate` exports only after meaningful graph changes or when requested.
- `close-case` exports Markdown and Mermaid after successful closure.
- Do not edit exported files as a way to update case truth.
