---
name: discuss-case
description: This skill should be used when the user asks to "discuss the case", "brainstorm about the investigation", "I'm stuck", "what do you think", or when the investigation loop detects a deadlock, hypothesis ambiguity, or needs user input to break a tie. Facilitates structured case discussion.
---

# Discuss Case — Structured Investigation Dialogue

Conduct a case discussion with the user at critical investigation junctures. Present the situation clearly, surface key uncertainties, and integrate user input as high-weight evidence.

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

User input enters the board as high-priority fragments:

| User Says | Fragment Created |
|-----------|----------------|
| States a fact | `role: observation, maturity: evidence, source: user_authority` |
| Suggests a theory | `role: hypothesis, maturity: clue, confidence: 0.7, source: user_input` |
| Eliminates a direction | `role: constraint, maturity: anchor, source: user_authority` + eliminates thread |
| Points to a clue | `role: observation, maturity: clue, confidence: 0.8, source: user_input` |
| Adjusts priority | Update action scoring weights, no new fragment |

User-authority fragments have elevated status:
- `source: user_authority` fragments start at higher maturity
- Constraints from user are treated as hard constraints (anchor-level)
- User hypotheses get a confidence boost (+0.2 over default)

## After Discussion

1. Update the board with new fragments/threads from user input
2. Re-run constraint propagation
3. Re-assess phase
4. Report what changed:

> "Based on your input, I've [updated X, eliminated Y, added Z]. The investigation now points toward [direction]. Continuing with `/detective:investigate`."

5. Return control to the investigate loop (or pause if user prefers)

## Tone

Speak as a detective colleague — professional, direct, no unnecessary formality. Acknowledge uncertainty honestly. Never pretend confidence that doesn't exist in the data.

## Additional Resources

### Scripts
- **`scripts/board.py`** — Add user-provided fragments to the board
- **`scripts/scoring.py`** — Re-run constraint propagation after discussion
