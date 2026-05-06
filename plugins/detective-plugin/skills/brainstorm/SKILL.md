---
name: brainstorm
description: This skill should be used when the user has a vague problem, wants to think through what to investigate before opening a case, says "I'm not sure what's wrong", "help me think about this", "let's figure out what to investigate", or needs collaborative exploration of the problem space before committing to a structured investigation. Produces a case brief that feeds directly into open-case.
---

# Brainstorm — Collaborative Problem Exploration Before Investigation

Help the user transform a vague concern, symptom, or question into a well-scoped case brief through natural dialogue. This is the THINKING phase before the DOING phase.

<HARD-GATE>
Do NOT invoke open-case, investigate, or any investigation action until you have produced a case brief and the user has approved it. Even if the problem seems obvious — brainstorm first, investigate second.
</HARD-GATE>

## Why This Exists

`open-case` expects a reasonably defined problem and goal. But users often arrive with:
- "Something feels off but I can't pinpoint it"
- "This broke and I have no idea where to start"
- "I have a hunch but no evidence yet"
- "Multiple things might be wrong simultaneously"

This skill bridges that gap — structured thinking before structured investigating.

## Checklist

Complete these steps in order:

1. **Gather context** — explore the environment (files, logs, recent changes, error messages)
2. **Identify the pain** — ask what's wrong, one question at a time
3. **Surface assumptions** — what does the user already believe? (these become initial hypotheses)
4. **Map the problem space** — propose 2-3 framings of what might be going on
5. **Scope the investigation** — agree on boundaries, budget, and success criteria
6. **Produce case brief** — structured summary ready for `open-case`
7. **User approves brief** — only then transition

## Process

### Phase 1: Context Gathering

Silently explore the environment to build your own understanding:
- Check recent git log, file changes, error logs
- Read relevant files the user mentions
- Look for recent breakage signals

Do NOT dump findings on the user. Use them to ask better questions.

### Phase 2: One Question at a Time

Ask clarifying questions sequentially. Each message = ONE question. Prefer structured choices when possible:

**Good patterns:**
> "When did this start? (a) After yesterday's deploy (b) It's been gradual (c) I just noticed it today"

> "What's the impact? (a) Blocking production (b) Degraded performance (c) Cosmetic / annoyance (d) Not sure yet"

> "Do you suspect a specific area, or is this wide open?"

**Bad patterns:**
- Multiple questions in one message
- Open-ended questions when multiple-choice would work
- Asking things you could discover yourself from the codebase

### Phase 3: Surface Assumptions

People carry implicit theories. Extract them explicitly:

> "It sounds like you suspect [X]. How confident are you — gut feeling, or have you seen evidence?"

> "You mentioned [Y]. Is that something you know happened, or something you're worried might have happened?"

Every assumption surfaced becomes either:
- An initial hypothesis (if speculative)
- An initial clue (if partially confirmed)
- A constraint (if definitively known)

### Phase 4: Propose Problem Framings

Once you have enough signal, propose 2-3 ways to frame the investigation:

```
I see a few ways to approach this:

1. **Narrow hunt**: Focus on [specific hypothesis]. Fast if correct, dead end if not.
   - Best if: you're fairly confident about the cause
   - Risk: tunnel vision

2. **Differential diagnosis**: Test multiple hypotheses in parallel.
   - Best if: genuinely unclear what's wrong
   - Risk: slower, broader

3. **Symptom trace**: Follow the observable symptoms backward to their source.
   - Best if: the symptoms are clear even if the cause isn't
   - Risk: may get lost in intermediate layers
```

Include your recommendation and why.

### Phase 5: Scope Agreement

Before producing the brief, confirm:
- **Goal**: What does "solved" look like?
- **Budget**: How much time/effort is appropriate? (maps to `max_actions`)
- **Boundaries**: What's out of scope?
- **Check-in frequency**: How often should the investigation pause for discussion?

### Phase 6: Produce Case Brief

Synthesize everything into a structured brief:

```markdown
## Case Brief: <title>

**Crime Scene**: <what's wrong, in one paragraph>
**Goal**: <what "solved" means>
**Scope**: <what's in / out>

**Initial Hypotheses**:
1. [Hypothesis] — confidence: [high/medium/low], basis: [why user thinks this]
2. [Hypothesis] — confidence: [high/medium/low], basis: [why]

**Initial Clues**:
- [Known fact relevant to the case]
- [Observed symptom]

**Constraints**:
- [Hard boundary — things we know for certain]
- [Resource limit — time/effort budget]

**Investigation Approach**: [which framing from Phase 4]
**Budget**: [max_actions] actions, checkpoint every [interval]

**Suggested First Move**: [where to start]
```

### Phase 7: Approval and Transition

Present the brief and ask:

> "Here's the case brief. Does this capture what we're investigating? Anything to add or change before I open the case?"

On approval:
- Invoke `detective:open-case` with the brief as structured input
- The brief maps directly to initial fragments:
  - Crime Scene → observation/evidence
  - Goal → observation/anchor (is_goal: true)
  - Hypotheses → hypothesis/clue
  - Clues → observation/clue
  - Constraints → constraint/anchor

## Key Principles

- **One question per message** — don't overwhelm
- **Prefer multiple choice** — lower cognitive load
- **Extract implicit theories** — users know more than they think
- **Propose, don't prescribe** — always offer alternatives with trade-offs
- **No premature investigation** — thinking is not wasted time
- **Respect the user's instinct** — if they have a strong hunch, weight it appropriately

## Anti-Patterns

| Don't | Do Instead |
|-------|-----------|
| Jump to "let me check the logs" | Ask what the user has already checked |
| Propose a solution before understanding the problem | Explore the problem space first |
| Ask 5 questions at once | One question, wait, next question |
| Ignore the user's intuition | Surface it, name it, weigh it |
| Make the brainstorm feel like an interrogation | Natural conversation, collaborative tone |
| Spend 20 minutes brainstorming a trivial problem | Scale effort to complexity — simple = short |

## Scaling to Complexity

- **Trivial problem** (user already knows what's wrong): 2-3 questions → brief → done. Total: ~2 minutes.
- **Medium problem** (user has symptoms, no clear cause): 5-7 questions → framing → brief. Total: ~5 minutes.
- **Complex problem** (vague, multi-dimensional): Full process, possibly decompose into sub-investigations.

Don't make simple things complicated. If the user says "the deploy broke the login page" — you don't need to explore 3 framings. Confirm scope, produce brief, move on.

## Tone

Curious colleague, not interrogator. Think: two detectives at a whiteboard, coffee in hand, sketching theories before hitting the street.
