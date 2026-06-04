---
name: open-case
description: This skill should be used when the user asks to "open a case", "start an investigation", "investigate this problem", "begin detective mode", or wants to apply structured investigation methodology to solve an unknown-target problem. Initializes a CaseBoard and begins the case-opening phase.
---

# Open Case — Initialize a Detective Investigation

Start a new investigation by creating a CaseBoard and establishing the case foundation with the user.

## Process

### 1. Understand the Problem

Before creating the case, conduct a brief exchange with the user to understand:
- What triggered this investigation (the "crime scene")
- What the desired outcome looks like (can be vague — "find the cause" is valid)
- Any initial clues or suspicions they already have
- Resource constraints (time budget, action limits)

If the user provided a clear problem description as an argument, skip directly to case creation.

### 2. Create the MCP-backed CaseBoard

For Detective v2/v2.1 cases, create the case through `detective_open_case`:

```text
detective_open_case(title="<title>", description="<description>", case_id="<case-id>", config={...})
```

Use a slug derived from the title as `<case-id>` (e.g., "perf-regression-2026-05"). If the Detective MCP server is unavailable, stop and ask the user to check `/mcp`.

### 3. Seed Initial Nodes

Add founding graph nodes through `detective_add_node`:

- Crime scene: `type="observation"`, `source="user"`, high confidence
- Case goal: `type="question"` or `type="task"`, `source="user"`, metadata `{"is_goal": true}`
- Initial clues: `type="clue"` or `type="observation"`, `source="user"`
- Initial hypotheses: `type="hypothesis"`, `source="user"`, confidence around `0.5`

Connect related founding nodes with `detective_add_edge` using `derives`, `supports`, `requires`, or `related_to` as appropriate.

### 4. Configure Investigation Parameters

Pass case-specific configuration to `detective_open_case` when creating the case:
- `checkpoint_interval`: How many actions between user check-ins (default: 5)
- `max_actions`: Budget limit (default: 50)
- `confidence_threshold_confirm`: When to confirm a hypothesis (default: 0.85)
- `confidence_threshold_eliminate`: When to eliminate or down-rank an alternative (default: 0.15)

Adjust based on problem complexity — simple problems: lower max_actions, higher checkpoint frequency.

### 5. Present the Board

After initialization, display a summary:
- Case title and ID
- Crime scene summary
- Goal statement
- Initial fragments count
- Suggested first investigation direction
- How to proceed (`/detective:investigate` to start the loop)

## Output Format

Present the initialized case to the user in this structure:

```
## Case Opened: <title>
ID: <case-id>
Phase: Opening

**Crime Scene**: <one-line summary>
**Goal**: <what we're solving>
**Initial Clues**: <count> fragments on board
**Budget**: <max_actions> actions, checkpoint every <interval>

**Suggested First Move**: <what to investigate first>

Run `/detective:investigate` to begin the investigation loop.
```

## State File Location

For v2/v2.1 cases, canonical state is created by `detective_open_case` at:

```text
.detective/cases/<case-id>/case.json
```

Do not create or edit case JSON files directly for v2/v2.1 cases.

## Legacy v1 fallback resources

Use these only for legacy v1 flat JSON case files when the Detective MCP server is unavailable:

- **`scripts/board.py`** — Legacy v1 CaseBoard inspection and deprecated mutation helpers
