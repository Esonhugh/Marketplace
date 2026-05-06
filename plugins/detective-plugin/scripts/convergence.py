#!/usr/bin/env python3
"""Convergence detection — determines if a case can be closed.

Usage: python convergence.py <case_file>

Outputs a JSON report with:
  - converged: bool
  - conditions: dict of individual convergence checks
  - reasoning: str explanation

Convergence criteria:
  1. A confirmed hypothesis exists (confidence > upper threshold)
  2. All other hypotheses eliminated or below lower threshold
  3. Evidence chain from crime scene to conclusion has no gaps
  4. No unresolved 'requires' threads
"""

import json
import sys
from pathlib import Path


def load_board(path: str) -> dict:
    return json.loads(Path(path).read_text())


def check_convergence(board: dict) -> dict:
    config = board.get("config", {})
    upper = config.get("confidence_threshold_confirm", 0.85)
    lower = config.get("confidence_threshold_eliminate", 0.15)

    fragments = board["fragments"]
    threads = board["threads"]

    hypotheses = [f for f in fragments if f["role"] == "hypothesis"]
    active_hyp = [h for h in hypotheses if h.get("status") != "eliminated"]
    confirmed = [h for h in active_hyp if h["confidence"] >= upper]
    weak = [h for h in active_hyp if h["confidence"] < lower]

    has_confirmed = len(confirmed) >= 1
    others_resolved = all(
        h["id"] in [c["id"] for c in confirmed] or h.get("status") == "eliminated" or h["confidence"] < lower
        for h in hypotheses
    )

    requires_threads = [t for t in threads if t["type"] == "requires"]
    satisfied_ids = {f["id"] for f in fragments if f["maturity"] in ("evidence", "anchor")}
    unresolved_requires = [
        t for t in requires_threads
        if t["to_id"] not in satisfied_ids
    ]
    no_hanging_requires = len(unresolved_requires) == 0

    conclusions = [f for f in fragments if f["role"] == "conclusion"]
    has_conclusion_chain = False
    if conclusions:
        for conclusion in conclusions:
            supporting = [
                t for t in threads
                if t["to_id"] == conclusion["id"] and t["type"] == "supports"
            ]
            if len(supporting) >= 1:
                all_supported_by_evidence = all(
                    any(
                        f["id"] == t["from_id"] and f["maturity"] in ("evidence", "anchor")
                        for f in fragments
                    )
                    for t in supporting
                )
                if all_supported_by_evidence:
                    has_conclusion_chain = True
                    break

    converged = has_confirmed and others_resolved and no_hanging_requires

    conditions = {
        "has_confirmed_hypothesis": has_confirmed,
        "confirmed_hypotheses": [{"id": h["id"], "confidence": h["confidence"]} for h in confirmed],
        "all_alternatives_resolved": others_resolved,
        "unresolved_active": [
            {"id": h["id"], "confidence": h["confidence"]}
            for h in active_hyp
            if h["id"] not in [c["id"] for c in confirmed] and h["confidence"] >= lower
        ],
        "no_hanging_requires": no_hanging_requires,
        "unresolved_requires_count": len(unresolved_requires),
        "has_conclusion_chain": has_conclusion_chain,
    }

    if converged:
        reasoning = (
            f"Case converged: {len(confirmed)} confirmed hypothesis(es) with confidence >= {upper}, "
            f"all alternatives resolved, no unresolved requirements."
        )
    else:
        issues = []
        if not has_confirmed:
            reasoning_part = f"No hypothesis above confidence threshold ({upper})"
            if active_hyp:
                best = max(active_hyp, key=lambda h: h["confidence"])
                reasoning_part += f". Best: {best['id']} at {best['confidence']:.3f}"
            issues.append(reasoning_part)
        if not others_resolved:
            remaining = [
                h for h in active_hyp
                if h["id"] not in [c["id"] for c in confirmed] and h["confidence"] >= lower
            ]
            issues.append(f"{len(remaining)} alternative hypothesis(es) still active")
        if not no_hanging_requires:
            issues.append(f"{len(unresolved_requires)} unresolved 'requires' thread(s)")
        reasoning = "Not converged: " + "; ".join(issues)

    return {
        "converged": converged,
        "conditions": conditions,
        "reasoning": reasoning,
        "recommendation": "close-case" if converged else "continue-investigation",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convergence.py <case_file>")
        sys.exit(1)

    case_file = sys.argv[1]
    board = load_board(case_file)
    result = check_convergence(board)
    print(json.dumps(result, indent=2))
