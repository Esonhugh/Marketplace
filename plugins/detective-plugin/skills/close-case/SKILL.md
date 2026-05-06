---
name: close-case
description: This skill should be used when the user asks to "close the case", "conclude the investigation", "wrap up", "present findings", or when the convergence check indicates the case has been solved. Produces the final resolution with complete evidence chain.
---

# Close Case — Conclude Investigation with Resolution

Produce the final investigation resolution: a confirmed conclusion supported by a complete, traceable evidence chain from initial clues to final answer.

## Prerequisites

Check convergence before closing:

```bash
python $PLUGIN_ROOT/scripts/convergence.py .detective/cases/<case-id>.json
```

- If converged → proceed with closing
- If NOT converged → inform the user which conditions are unmet. Ask: "Close anyway with partial conclusion, or continue investigating?"

## Closing Process

### 1. Identify the Conclusion

Find the confirmed hypothesis (highest confidence, meeting threshold):
- Read the board's active hypotheses
- Select the one with confidence >= threshold (or highest if forced close)
- This becomes the **Resolution**

### 2. Trace the Evidence Chain

Build the complete logical chain from crime scene to conclusion:

1. Start from the confirmed hypothesis
2. Follow `supports` threads backwards to find supporting evidence
3. For each evidence piece, follow `derives` threads to find its origins
4. Continue until reaching fragments with `source: user_authority` or initial observations

Present as a numbered chain:
```
1. [Crime Scene] <initial observation>
2. [Clue → Evidence] <first finding> (verified by: <action>)
3. [Evidence] <second finding> (supports hypothesis via: <reasoning>)
4. [Constraint] <elimination rule> (eliminated alternatives: <list>)
5. [Conclusion] <final answer> (confidence: <X>)
```

### 3. Document Eliminated Alternatives

List all hypotheses that were considered and why they were ruled out:

```
### Ruled Out
- <Hypothesis A>: Eliminated because <reason> (evidence: <fragment id>)
- <Hypothesis B>: Confidence decayed to <X> due to <contradicting evidence>
```

### 4. Write Resolution Report

Create a markdown summary file:

```bash
# Write to .detective/cases/<case-id>-resolution.md
```

Format:
```markdown
# Case Resolution: <title>

## Conclusion
<one paragraph stating the final answer>

## Evidence Chain
<numbered list from step 2>

## Eliminated Alternatives
<list from step 3>

## Investigation Statistics
- Total rounds: <N>
- Actions taken: <N>
- Fragments created: <N>
- Hypotheses considered: <N> (confirmed: 1, eliminated: <N>)
- Time span: <first action> to <last action>

## Confidence Assessment
- Primary conclusion confidence: <X>
- Evidence chain completeness: <complete/has gaps>
- Remaining uncertainties: <any caveats>
```

### 5. Update Board State

Mark the case as closed:
- Set board `phase` to "resolution"
- Add a conclusion fragment: `{"role": "conclusion", "maturity": "anchor", "confidence": <X>}`
- Add `derives` threads from supporting evidence to the conclusion

### 6. Present to User

Display the resolution in conversation:

```
## Case Closed: <title>

**Conclusion**: <answer>
**Confidence**: <X>%
**Evidence Chain**: <count> links, fully traced

<brief narrative of how we got here>

Full report saved to: .detective/cases/<case-id>-resolution.md
```

## Forced Close (Partial Resolution)

When closing without full convergence:

- Mark confidence appropriately (lower)
- Explicitly state which conditions are unmet
- List remaining open questions
- Note this is a "partial resolution" in the report
- Add caveat: "Investigation paused, not conclusively resolved"

## Post-Close

After closing, the case file remains for reference. Suggest:
- "The case file is preserved at `.detective/cases/<case-id>.json` for future reference."
- "To reopen, run `/detective:investigate <case-id>` — the board state is intact."

## Additional Resources

### Scripts
- **`scripts/convergence.py`** — Check if convergence criteria are met
- **`scripts/board.py`** — Read board state, add conclusion fragment
