from detective_mcp.legacy_board import eliminate_fragment, load_board, save_board


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
        fragment for fragment in board["fragments"]
        if fragment["role"] == "constraint" and fragment["maturity"] in ("evidence", "anchor")
    ]
    hypotheses = {
        fragment["id"]: fragment for fragment in board["fragments"]
        if fragment["role"] == "hypothesis" and fragment.get("status") != "eliminated"
    }

    for thread in board["threads"]:
        if thread["type"] == "eliminates":
            target = hypotheses.get(thread["to_id"])
            if target and target.get("status") != "eliminated":
                source = next((fragment for fragment in constraints if fragment["id"] == thread["from_id"]), None)
                if source:
                    eliminate_fragment(board, target["id"], f"Eliminated by constraint {source['id']}")
                    changes["eliminated"].append(target["id"])

        elif thread["type"] == "contradicts":
            target = hypotheses.get(thread["to_id"])
            if target and target.get("status") != "eliminated":
                source_fragment = next(
                    (fragment for fragment in board["fragments"] if fragment["id"] == thread["from_id"]),
                    None,
                )
                if source_fragment and source_fragment["maturity"] in ("evidence", "anchor"):
                    decay = 0.15
                    target["confidence"] = max(0.0, target["confidence"] - decay)
                    changes["weakened"].append({
                        "id": target["id"],
                        "new_confidence": round(target["confidence"], 3),
                    })

    threshold = board.get("config", {}).get("confidence_threshold_eliminate", 0.15)
    for hypothesis in hypotheses.values():
        if hypothesis.get("status") != "eliminated" and hypothesis["confidence"] < threshold:
            reason = f"Confidence {hypothesis['confidence']:.3f} below threshold {threshold}"
            eliminate_fragment(board, hypothesis["id"], reason)
            changes["eliminated"].append(hypothesis["id"])

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
    active_hypothesis_ids = {
        fragment["id"] for fragment in board["fragments"]
        if fragment["role"] == "hypothesis" and fragment.get("status") != "eliminated"
    }
    total_active = max(len(active_hypothesis_ids), 1)

    scored = []
    for action in candidates:
        relevant = [hypothesis_id for hypothesis_id in action.get("target_hypotheses", []) if hypothesis_id in active_hypothesis_ids]
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

    scored.sort(key=lambda item: item["score"], reverse=True)
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
    active_hypotheses = [
        fragment for fragment in fragments
        if fragment["role"] == "hypothesis" and fragment.get("status") != "eliminated"
    ]
    eliminated_hypotheses = [
        fragment for fragment in fragments
        if fragment["role"] == "hypothesis" and fragment.get("status") == "eliminated"
    ]
    evidence_count = sum(1 for fragment in fragments if fragment["maturity"] in ("evidence", "anchor"))
    clue_count = sum(1 for fragment in fragments if fragment["maturity"] == "clue")
    thread_density = len(threads) / max(total, 1)

    if total < 5:
        phase = "opening"
        reason = "Few fragments on board, investigation just starting"
    elif len(active_hypotheses) == 0 and clue_count > 0:
        phase = "survey"
        reason = "Clues present but no hypotheses formed yet"
    elif len(active_hypotheses) >= 3 and thread_density < 0.5:
        phase = "pursuit"
        reason = f"{len(active_hypotheses)} active hypotheses with sparse connections"
    elif len(eliminated_hypotheses) > 0 and thread_density >= 0.5:
        phase = "convergence"
        reason = f"Hypotheses being eliminated, thread density {thread_density:.2f}"
    elif 1 <= len(active_hypotheses) <= 2 and evidence_count >= 3:
        phase = "closing"
        reason = f"Only {len(active_hypotheses)} hypothesis(es) remain with {evidence_count} evidence pieces"
    else:
        phase = "pursuit"
        reason = "Active investigation in progress"

    return {
        "suggested_phase": phase,
        "reason": reason,
        "stats": {
            "total_fragments": total,
            "active_hypotheses": len(active_hypotheses),
            "eliminated_hypotheses": len(eliminated_hypotheses),
            "evidence_count": evidence_count,
            "clue_count": clue_count,
            "thread_density": round(thread_density, 3),
        },
    }
