from pathlib import Path
from typing import Any

from . import store
from .models import DEFAULT_CONFIG


INACTIVE_HYPOTHESIS_STATUSES = {"rejected", "stale", "resolved"}


def _summarize_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node["id"],
        "content": node["content"],
        "status": node["status"],
        "confidence": node["confidence"],
    }


def _confirmed_hypotheses(case: dict[str, Any], confirm_threshold: float) -> list[dict[str, Any]]:
    return [
        node
        for node in case["nodes"]
        if node["type"] == "hypothesis"
        and node["status"] not in INACTIVE_HYPOTHESIS_STATUSES
        and node["confidence"] >= confirm_threshold
    ]


def _has_direct_evidence_support(case: dict[str, Any], hypothesis_id: str) -> bool:
    evidence_ids = {node["id"] for node in case["nodes"] if node["type"] == "evidence"}
    return any(
        edge["type"] == "supports" and edge["from_id"] in evidence_ids and edge["to_id"] == hypothesis_id
        for edge in case["edges"]
    )


def _blocking_questions(case: dict[str, Any], confirmed_ids: set[str]) -> list[dict[str, Any]]:
    questions_by_id = {
        node["id"]: node
        for node in case["nodes"]
        if node["type"] == "question" and node["status"] == "open"
    }
    blocking_ids: set[str] = set()
    for edge in case["edges"]:
        if edge["type"] != "requires":
            continue
        if edge["from_id"] in questions_by_id and edge["to_id"] in confirmed_ids:
            blocking_ids.add(edge["from_id"])
    return [_summarize_node(questions_by_id[node_id]) for node_id in sorted(blocking_ids)]


def convergence_status(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    config = case.get("config", {})
    confirm_threshold = config.get("confidence_threshold_confirm", DEFAULT_CONFIG["confidence_threshold_confirm"])
    eliminate_threshold = config.get("confidence_threshold_eliminate", DEFAULT_CONFIG["confidence_threshold_eliminate"])

    confirmed = _confirmed_hypotheses(case, confirm_threshold)
    confirmed_ids = {node["id"] for node in confirmed}
    supported_confirmed = [node for node in confirmed if _has_direct_evidence_support(case, node["id"])]
    supported_confirmed_ids = {node["id"] for node in supported_confirmed}
    alternatives_open = [
        _summarize_node(node)
        for node in case["nodes"]
        if node["type"] == "hypothesis"
        and node["status"] not in INACTIVE_HYPOTHESIS_STATUSES
        and node["id"] not in supported_confirmed_ids
        and node["confidence"] >= eliminate_threshold
    ]
    blocking_questions = _blocking_questions(case, supported_confirmed_ids)

    converged = bool(confirmed) and bool(supported_confirmed) and not alternatives_open and not blocking_questions

    reasons: list[str] = []
    if not confirmed:
        reasons.append(f"no active hypothesis meets confirm threshold {confirm_threshold:.2f}")
    if confirmed and not supported_confirmed:
        reasons.append("confirmed hypotheses lack direct evidence support")
    if alternatives_open:
        count = len(alternatives_open)
        noun = "hypothesis remains" if count == 1 else "hypotheses remain"
        reasons.append(f"{count} active alternative {noun} above eliminate threshold {eliminate_threshold:.2f}")
    if blocking_questions:
        count = len(blocking_questions)
        noun = "question" if count == 1 else "questions"
        reasons.append(f"{count} blocking open {noun} require a confirmed hypothesis")
    if not reasons:
        reasons.append("confirmed hypothesis has direct evidence support, alternatives are resolved, and no open questions block closure")

    return {
        "case_id": case_id,
        "converged": converged,
        "confirmed_hypotheses": [_summarize_node(node) for node in supported_confirmed],
        "blocking_questions": blocking_questions,
        "alternatives_open": alternatives_open,
        "reason": "; ".join(reasons),
        "recommendation": "close-case" if converged else "continue-investigation",
    }


def deadlock_status(
    workspace: str | Path | None,
    case_id: str,
    scored_actions: list[dict[str, Any]],
    recent_new_nodes: int = 0,
    recent_new_edges: int = 0,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    config = case.get("config", {})
    threshold = config.get("deadlock_score_threshold", DEFAULT_CONFIG["deadlock_score_threshold"])

    has_recent_graph_changes = recent_new_nodes > 0 or recent_new_edges > 0
    scores = [float(action.get("score", 0.0)) for action in scored_actions]
    all_scores_low = bool(scores) and all(score < threshold for score in scores)
    deadlocked = bool(scored_actions) and all_scores_low and not has_recent_graph_changes

    if not scored_actions:
        reason = "no scored actions available"
    elif has_recent_graph_changes:
        reason = f"recent graph changes detected ({recent_new_nodes} new node(s), {recent_new_edges} new edge(s))"
    elif not all_scores_low:
        reason = f"at least one candidate action meets or exceeds deadlock threshold {threshold:.2f}"
    else:
        reason = f"all candidate actions below deadlock threshold {threshold:.2f} and no recent graph changes"

    return {
        "case_id": case_id,
        "deadlocked": deadlocked,
        "reason": reason,
        "recommendation": "discuss-case" if deadlocked else "continue-investigation",
    }
