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

### 2. Create the CaseBoard

Initialize the case using the board script:

```bash
python $PLUGIN_ROOT/scripts/board.py init .detective/cases/<case-id>.json "<title>" "<description>"
```

Use a slug derived from the title as `<case-id>` (e.g., "perf-regression-2026-05").

### 3. Seed Initial Fragments

Add the founding fragments to the board:

**Crime Scene** (always required):
```json
{"content": "<initial context>", "role": "observation", "maturity": "evidence", "source": "user_authority"}
```

**Case Goal** (always required):
```json
{"content": "<what we're trying to determine>", "role": "observation", "maturity": "anchor", "source": "user_authority", "metadata": {"is_goal": true}}
```

**Initial Clues** (if user provided any):
```json
{"content": "<clue>", "role": "observation", "maturity": "clue", "source": "user_input"}
```

**Initial Hypotheses** (if user has suspicions):
```json
{"content": "<hypothesis>", "role": "hypothesis", "maturity": "clue", "confidence": 0.5, "source": "user_input"}
```

### 4. Configure Investigation Parameters

Set case-specific configuration by updating the board JSON:
- `checkpoint_interval`: How many actions between user check-ins (default: 5)
- `max_actions`: Budget limit (default: 50)
- `confidence_threshold_confirm`: When to confirm a hypothesis (default: 0.85)
- `confidence_threshold_eliminate`: When to auto-eliminate (default: 0.15)

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

All case files stored at: `.detective/cases/<case-id>.json` (project-local)

Create the `.detective/cases/` directory if it doesn't exist.

## Additional Resources

### Scripts
- **`scripts/board.py`** — CaseBoard CRUD operations (init, add-fragment, add-thread, status)
