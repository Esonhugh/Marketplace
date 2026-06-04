---
name: discuss-case
description: This skill should be used when the user asks to "discuss the case", "brainstorm about the investigation", "I'm stuck", "what do you think", or when the investigation loop detects a deadlock, hypothesis ambiguity, or needs user input to break a tie. Facilitates structured case discussion.
---

# Discuss Case — Structured Investigation Dialogue

Conduct a case discussion with the user at critical investigation junctures. Present the situation clearly, surface key uncertainties, and integrate user input as high-weight evidence.

## MCP-first user guidance

When the user provides guidance, write it through `detective_apply_user_guidance`:

- Facts → `guidance_type="fact"`
- Theories → `guidance_type="theory"`
- Boundaries or disallowed directions → `guidance_type="constraint"`
- New uncertainties → `guidance_type="question"`

After applying guidance, call `detective_graph_overview` before continuing. User guidance has priority over automated scheduling.

## When This Triggers

Automatic triggers (from investigate loop):
- Multiple hypotheses with confidence spread < 0.1 (ambiguity)
- All candidate actions scoring below 0.3 (deadlock)
- Previously strong hypothesis just eliminated (direction change)
- Budget > 80% consumed (approaching limit)
- Phase regression detected (new evidence contradicted main theory)

Manual trigger: user explicitly calls `/detective:discuss-case`

## Discussion Structure

Every case discussion follows this four-part format:

### Part 1: Case Summary (Brief)

One paragraph summarizing the current state in plain language. No jargon, no fragment IDs — speak like a detective briefing a colleague:

> "We're investigating [problem]. So far we've established [key facts]. Our leading theory is [hypothesis] but [complication]."

### Part 2: Key Uncertainty (The Fork)

Identify the 1-2 most critical points of uncertainty that are blocking progress:

> "The main question right now is: [specific question]. This matters because [why it's blocking]."

If there's a tie between hypotheses, present them as alternatives:

> "Two theories are equally plausible right now:
> 1. [Hypothesis A] — supported by [evidence], confidence [X]
> 2. [Hypothesis B] — supported by [evidence], confidence [Y]"

### Part 3: Detective's Inclination

State what the system would do next if acting autonomously, and why:

> "My instinct says [direction] because [reasoning]. But I'm [X]% confident in this — [what could be wrong]."

### Part 4: Ask the User

Pose a specific, actionable question. Prefer structured options when possible:

- "Do you have any domain knowledge that could distinguish between these two theories?"
- "Should I prioritize [A] or [B] given your context?"
- "Is there a source of information I haven't considered?"
- "Should I abandon [direction] and try something new?"

## Processing User Response

For v2/v2.1 cases, user input enters the graph only through `detective_apply_user_guidance`:

| User Says | MCP Guidance Mapping |
|-----------|----------------------|
| States a fact | `guidance_type="fact"` |
| Suggests a theory | `guidance_type="theory"` |
| Eliminates a direction | `guidance_type="constraint"` |
| Points to a clue or uncertainty | `guidance_type="question"` |
| Adjusts priority | Apply through MCP-backed scheduling or guidance; do not mutate files directly |

User-authority fragments have elevated status:
- `source: user_authority` fragments start at higher maturity
- Constraints from user are treated as hard constraints (anchor-level)
- User hypotheses get a confidence boost (+0.2 over default)

## After Discussion

1. Apply any user input with `detective_apply_user_guidance` if it was not already applied.
2. Call `detective_graph_overview` to review the updated MCP-backed graph state.
3. Use Detective MCP tools for any follow-up state changes, exports, or scheduling updates.
4. Report what changed:

> "Based on your input, I've [updated X, eliminated Y, added Z]. The investigation now points toward [direction]. Continuing with `/detective:investigate`."

5. Return control to the investigate loop (or pause if user prefers)

## Tone

Speak as a detective colleague — professional, direct, no unnecessary formality. Acknowledge uncertainty honestly. Never pretend confidence that doesn't exist in the data.

## Legacy v1 fallback resources

These scripts are deprecated fallback references only for legacy v1 flat JSON case files when the Detective MCP server is unavailable. For v2/v2.1 cases, user guidance and any state changes must go through Detective MCP tools.

### Scripts
- **`scripts/board.py`** — Legacy v1 board inspection and deprecated user-fragment helpers
- **`scripts/scoring.py`** — Legacy v1 scoring and deprecated propagation helpers
