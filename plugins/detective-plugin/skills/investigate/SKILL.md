---
name: investigate
description: This skill should be used when the user asks to "investigate", "continue the investigation", "run the detective loop", "next investigation step", or wants to execute the Scan-Evolve-Focus-Act-File cycle on an active case. Runs the core investigation loop with periodic checkpoints.
---

# Investigate — Core Detective Loop

Execute the investigation cycle on an active case: Scan → Evolve → Focus → Act → File. Run multiple rounds until a checkpoint is reached or convergence is detected.

## Prerequisites

An active case must exist in `.detective/cases/`. If multiple cases exist and no case-id argument is provided, ask the user which case to work on.

## The Investigation Cycle

Each round follows five steps:

### Step 1: Scan (Review the Board)

Read the current CaseBoard state and analyze the graph topology:

```bash
python $PLUGIN_ROOT/scripts/board.py status .detective/cases/<case-id>.json
python $PLUGIN_ROOT/scripts/scoring.py suggest-phase .detective/cases/<case-id>.json
```

Assess:
- Which Fragments are isolated (no threads connecting them)?
- Which Threads are broken (connecting to eliminated fragments)?
- Which Hypotheses are unsupported (no supporting evidence)?
- What is the current phase?

### Step 2: Evolve (Propagate Constraints & Mature Fragments)

Run constraint propagation to automatically update the board:

```bash
python $PLUGIN_ROOT/scripts/scoring.py propagate .detective/cases/<case-id>.json
```

Additionally, assess whether any Fragment should be promoted:
- Raw observations with corroboration → promote to Clue
- Clues verified by investigation actions → promote to Evidence
- Evidence forming indisputable anchors → promote to Anchor

Use `board.py evolve <case-file> <fragment-id> <new-maturity>` for promotions.

### Step 3: Focus (Strategy & Prioritization)

This is the critical decision step. Determine the highest-value next action:

1. Generate 2-5 candidate investigation actions based on:
   - Gaps in the evidence graph
   - Unsupported hypotheses needing verification
   - Promising clues needing follow-up
   - Contradictions needing resolution

2. Score candidates:
```bash
python $PLUGIN_ROOT/scripts/scoring.py score-actions .detective/cases/<case-id>.json '<json array of candidates>'
```

Each candidate needs: `description`, `target_hypotheses` (which hypotheses it discriminates), `feasibility` (0-1), `cost` (1-10).

3. Apply pruning heuristics:
   - Skip actions targeting eliminated hypotheses
   - Skip actions whose expected outcome duplicates existing evidence
   - Deprioritize directions that have been cold (3+ actions with no new evidence)

4. Select the top-scoring action to execute.

### Step 4: Act (Execute Investigation Action)

Execute the chosen action using available Claude Code tools:
- File reading/searching for code investigation
- Bash commands for system exploration
- Web search for research/intelligence gathering
- Any MCP tools available in the session

Record what was done in `actions_history`:
```json
{"action": "<description>", "tools_used": ["Bash"], "timestamp": "<iso>", "round": <n>}
```

### Step 5: File (Record Results)

Process action results and update the board:

1. **Create new Fragments** from findings:
   - New observations → `{"role": "observation", "maturity": "raw"}`
   - Confirmed facts → `{"role": "observation", "maturity": "evidence"}`
   - New hypotheses formed → `{"role": "hypothesis", "maturity": "clue", "confidence": 0.5}`
   - Constraints discovered → `{"role": "constraint", "maturity": "evidence"}`

2. **Add Threads** connecting new fragments to existing ones:
   - New evidence supporting a hypothesis → `supports` thread
   - New evidence contradicting a hypothesis → `contradicts` thread
   - Derived conclusions → `derives` thread

3. **Update the board file**:
```bash
python $PLUGIN_ROOT/scripts/board.py add-fragment .detective/cases/<case-id>.json '<json>'
python $PLUGIN_ROOT/scripts/board.py add-thread .detective/cases/<case-id>.json '<json>'
```

## Checkpoint Logic

After every N rounds (configured as `checkpoint_interval` in case config, default 5):

1. Check convergence:
```bash
python $PLUGIN_ROOT/scripts/convergence.py .detective/cases/<case-id>.json
```

2. If converged → suggest closing the case with `/detective:close-case`

3. If not converged → present a checkpoint summary to the user:
   - Rounds completed this session
   - New fragments/threads added
   - Hypotheses eliminated
   - Current leading hypothesis and confidence
   - Suggested next direction
   - Ask: "Continue investigation, discuss the case, or pause?"

## Trigger Case Discussion

Automatically invoke `/detective:discuss-case` when:
- Multiple hypotheses have nearly equal confidence (spread < 0.1)
- All candidate actions score below 0.3 (stuck)
- A previously strong hypothesis just got eliminated
- Budget is > 80% consumed

## Loop Termination

Stop the loop when:
- Convergence detected (recommend close-case)
- User requests pause at checkpoint
- Action budget exhausted
- Discussion triggered (hand off to discuss-case skill)

## Round Output Format

For each round, briefly report:
```
[Round N | Phase: <phase>] Action: <what was done>
  → Found: <key finding summary>
  → Board: +<new fragments> fragments, +<new threads> threads
  → Hypotheses: <active count> active, <eliminated this round> eliminated
```

## Additional Resources

### Scripts
- **`scripts/board.py`** — Fragment/Thread CRUD, board status, graph export
- **`scripts/scoring.py`** — Constraint propagation, action scoring, phase detection
- **`scripts/convergence.py`** — Convergence condition checking
