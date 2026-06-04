"""Legacy convergence checks for classic Detective case boards.

Compatibility note: ``has_conclusion_chain`` is reported as an informational
condition only. Existing legacy convergence behavior is preserved: convergence
is gated by confirmed hypotheses, resolved alternatives, and no hanging
``requires`` threads, not by the informational conclusion-chain condition.
"""

from detective_mcp.legacy_board import load_board


def check_convergence(board: dict) -> dict:
    config = board.get("config", {})
    upper = config.get("confidence_threshold_confirm", 0.85)
    lower = config.get("confidence_threshold_eliminate", 0.15)

    fragments = board["fragments"]
    threads = board["threads"]

    hypotheses = [fragment for fragment in fragments if fragment["role"] == "hypothesis"]
    active_hypotheses = [fragment for fragment in hypotheses if fragment.get("status") != "eliminated"]
    confirmed = [fragment for fragment in active_hypotheses if fragment["confidence"] >= upper]

    has_confirmed = len(confirmed) >= 1
    confirmed_ids = [fragment["id"] for fragment in confirmed]
    others_resolved = all(
        fragment["id"] in confirmed_ids or fragment.get("status") == "eliminated" or fragment["confidence"] < lower
        for fragment in hypotheses
    )

    requires_threads = [thread for thread in threads if thread["type"] == "requires"]
    satisfied_ids = {fragment["id"] for fragment in fragments if fragment["maturity"] in ("evidence", "anchor")}
    unresolved_requires = [thread for thread in requires_threads if thread["to_id"] not in satisfied_ids]
    no_hanging_requires = len(unresolved_requires) == 0

    conclusions = [fragment for fragment in fragments if fragment["role"] == "conclusion"]
    has_conclusion_chain = False
    if conclusions:
        for conclusion in conclusions:
            supporting = [
                thread for thread in threads
                if thread["to_id"] == conclusion["id"] and thread["type"] == "supports"
            ]
            if len(supporting) >= 1:
                all_supported_by_evidence = all(
                    any(
                        fragment["id"] == thread["from_id"] and fragment["maturity"] in ("evidence", "anchor")
                        for fragment in fragments
                    )
                    for thread in supporting
                )
                if all_supported_by_evidence:
                    has_conclusion_chain = True
                    break

    converged = has_confirmed and others_resolved and no_hanging_requires

    conditions = {
        "has_confirmed_hypothesis": has_confirmed,
        "confirmed_hypotheses": [{"id": fragment["id"], "confidence": fragment["confidence"]} for fragment in confirmed],
        "all_alternatives_resolved": others_resolved,
        "unresolved_active": [
            {"id": fragment["id"], "confidence": fragment["confidence"]}
            for fragment in active_hypotheses
            if fragment["id"] not in confirmed_ids and fragment["confidence"] >= lower
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
            if active_hypotheses:
                best = max(active_hypotheses, key=lambda fragment: fragment["confidence"])
                reasoning_part += f". Best: {best['id']} at {best['confidence']:.3f}"
            issues.append(reasoning_part)
        if not others_resolved:
            remaining = [
                fragment for fragment in active_hypotheses
                if fragment["id"] not in confirmed_ids and fragment["confidence"] >= lower
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
