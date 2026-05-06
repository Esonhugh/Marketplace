#!/usr/bin/env python3
"""Strategy scoring and constraint propagation engine.

Usage: python scoring.py <command> <case_file> [args...]

Commands:
  propagate <case_file>                 Run constraint propagation
  score-actions <case_file> <json>      Score candidate actions
  suggest-phase <case_file>             Suggest current investigation phase
"""

import json
import sys
from pathlib import Path


def load_board(path: str) -> dict:
    return json.loads(Path(path).read_text())


def save_board(board: dict, path: str):
    Path(path).write_text(json.dumps(board, indent=2, ensure_ascii=False))


def propagate_constraints(board: dict) -> dict:
    """Apply constraint propagation: constraints eliminate or weaken hypotheses.

    For each active constraint fragment:
    - Find hypotheses connected via 'eliminates' threads
    - Mark them as eliminated
    - Find hypotheses connected via 'contradicts' threads
    - Reduce their confidence by a decay factor

    Returns a report of changes made.
    """
    changes = {"eliminated": [], "weakened": []}
    constraints = [
        f for f in board["fragments"]
        if f["role"] == "constraint" and f["maturity"] in ("evidence", "anchor")
    ]
    hypotheses = {
        f["id"]: f for f in board["fragments"]
        if f["role"] == "hypothesis" and f.get("status") != "eliminated"
    }

    for thread in board["threads"]:
        if thread["type"] == "eliminates":
            target = hypotheses.get(thread["to_id"])
            if target and target.get("status") != "eliminated":
                source = next((f for f in constraints if f["id"] == thread["from_id"]), None)
                if source:
                    target["status"] = "eliminated"
                    target["elimination_reason"] = f"Eliminated by constraint {source['id']}"
                    changes["eliminated"].append(target["id"])

        elif thread["type"] == "contradicts":
            target = hypotheses.get(thread["to_id"])
            if target and target.get("status") != "eliminated":
                source_frag = next(
                    (f for f in board["fragments"] if f["id"] == thread["from_id"]),
                    None
                )
                if source_frag and source_frag["maturity"] in ("evidence", "anchor"):
                    decay = 0.15
                    target["confidence"] = max(0.0, target["confidence"] - decay)
                    changes["weakened"].append({
                        "id": target["id"],
                        "new_confidence": round(target["confidence"], 3),
                    })

    threshold = board.get("config", {}).get("confidence_threshold_eliminate", 0.15)
    for h in hypotheses.values():
        if h.get("status") != "eliminated" and h["confidence"] < threshold:
            h["status"] = "eliminated"
            h["elimination_reason"] = f"Confidence {h['confidence']:.3f} below threshold {threshold}"
            changes["eliminated"].append(h["id"])

    return changes


def score_candidate_actions(board: dict, candidates: list) -> list:
    """Score candidate actions by Discrimination × Feasibility / Cost.

    Each candidate should have:
      - description: str
      - target_hypotheses: list[str]  (hypothesis IDs this action could discriminate)
      - feasibility: float (0-1, estimated probability of useful result)
      - cost: float (1-10, resource cost estimate)

    Returns candidates sorted by score (highest first) with scores attached.
    """
    active_hyp_ids = {
        f["id"] for f in board["fragments"]
        if f["role"] == "hypothesis" and f.get("status") != "eliminated"
    }
    total_active = max(len(active_hyp_ids), 1)

    scored = []
    for action in candidates:
        relevant = [h for h in action.get("target_hypotheses", []) if h in active_hyp_ids]
        discrimination = len(relevant) / total_active
        feasibility = action.get("feasibility", 0.5)
        cost = max(action.get("cost", 5), 0.1)
        score = (discrimination * feasibility) / (cost / 10.0)
        scored.append({
            **action,
            "score": round(score, 4),
            "discrimination": round(discrimination, 4),
            "_relevant_hypotheses": len(relevant),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def suggest_phase(board: dict) -> dict:
    """Determine investigation phase from board topology.

    Phases:
      opening      - Few fragments, almost no threads
      survey       - Many clues, little evidence, no hypotheses
      pursuit      - Multiple active hypotheses, sparse threads
      convergence  - Hypotheses being eliminated, dense threads
      closing      - 1-2 hypotheses survive
      resolution   - Convergence criteria met
    """
    fragments = board["fragments"]
    threads = board["threads"]
    total = len(fragments)
    active_hyp = [
        f for f in fragments
        if f["role"] == "hypothesis" and f.get("status") != "eliminated"
    ]
    eliminated_hyp = [
        f for f in fragments
        if f["role"] == "hypothesis" and f.get("status") == "eliminated"
    ]
    evidence_count = sum(1 for f in fragments if f["maturity"] in ("evidence", "anchor"))
    clue_count = sum(1 for f in fragments if f["maturity"] == "clue")
    thread_density = len(threads) / max(total, 1)

    if total < 5:
        phase = "opening"
        reason = "Few fragments on board, investigation just starting"
    elif len(active_hyp) == 0 and clue_count > 0:
        phase = "survey"
        reason = "Clues present but no hypotheses formed yet"
    elif len(active_hyp) >= 3 and thread_density < 0.5:
        phase = "pursuit"
        reason = f"{len(active_hyp)} active hypotheses with sparse connections"
    elif len(eliminated_hyp) > 0 and thread_density >= 0.5:
        phase = "convergence"
        reason = f"Hypotheses being eliminated, thread density {thread_density:.2f}"
    elif 1 <= len(active_hyp) <= 2 and evidence_count >= 3:
        phase = "closing"
        reason = f"Only {len(active_hyp)} hypothesis(es) remain with {evidence_count} evidence pieces"
    else:
        phase = "pursuit"
        reason = "Active investigation in progress"

    return {
        "suggested_phase": phase,
        "reason": reason,
        "stats": {
            "total_fragments": total,
            "active_hypotheses": len(active_hyp),
            "eliminated_hypotheses": len(eliminated_hyp),
            "evidence_count": evidence_count,
            "clue_count": clue_count,
            "thread_density": round(thread_density, 3),
        }
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    case_file = sys.argv[2]

    if cmd == "propagate":
        board = load_board(case_file)
        changes = propagate_constraints(board)
        save_board(board, case_file)
        print(json.dumps(changes, indent=2))

    elif cmd == "score-actions":
        board = load_board(case_file)
        candidates = json.loads(sys.argv[3])
        scored = score_candidate_actions(board, candidates)
        print(json.dumps(scored, indent=2))

    elif cmd == "suggest-phase":
        board = load_board(case_file)
        result = suggest_phase(board)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
