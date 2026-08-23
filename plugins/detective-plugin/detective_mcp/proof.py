from pathlib import Path
from typing import Any

from . import coverage, store
from .ids import new_id, utc_now
from .models import CASE_STATUSES
from .validation import require_text, validate_choice

INACTIVE_HYPOTHESIS_STATUSES = {"rejected", "stale", "resolved"}
CONFIRMED_HYPOTHESIS_STATUS = "confirmed"


def _summarize_node(node: dict[str, Any]) -> dict[str, Any]:
    return {"id": node["id"], "content": node["content"], "status": node["status"], "confidence": node["confidence"]}


def _has_direct_confirming_evidence_support(case: dict[str, Any], hypothesis_id: str) -> bool:
    confirmed_evidence_ids = {
        node["id"]
        for node in case["nodes"]
        if node["type"] == "evidence" and node["status"] == CONFIRMED_HYPOTHESIS_STATUS
    }
    return any(
        edge["type"] == "supports" and edge["from_id"] in confirmed_evidence_ids and edge["to_id"] == hypothesis_id
        for edge in case["edges"]
    )


def _coverage_status_from_case(case: dict[str, Any]) -> dict[str, Any]:
    return coverage.status_from_case(case)


def _completion_signal(case: dict[str, Any]) -> dict[str, Any]:
    eliminate_threshold = case.get("config", {}).get("confidence_threshold_eliminate", 0.15)
    confirmed = [
        node
        for node in case["nodes"]
        if node["type"] == "hypothesis" and node["status"] == CONFIRMED_HYPOTHESIS_STATUS
    ]
    supported = [node for node in confirmed if _has_direct_confirming_evidence_support(case, node["id"])]
    supported_ids = {node["id"] for node in supported}
    alternatives = [
        _summarize_node(node)
        for node in case["nodes"]
        if node["type"] == "hypothesis"
        and node["status"] not in INACTIVE_HYPOTHESIS_STATUSES
        and node["id"] not in supported_ids
        and node["confidence"] >= eliminate_threshold
    ]
    blocking_questions = [_summarize_node(node) for node in case["nodes"] if node["type"] == "question" and node["status"] == "open"]
    complete = len(supported) == 1 and len(confirmed) == 1 and not alternatives and not blocking_questions
    blockers = []
    if not supported:
        blockers.append("no confirmed hypothesis has direct support from confirmed evidence")
    if alternatives:
        blockers.append(f"{len(alternatives)} active alternative hypothesis item(s)")
    if blocking_questions:
        blockers.append(f"{len(blocking_questions)} open question(s)")
    if len(confirmed) > 1:
        blockers.append("multiple confirmed hypotheses require explicit resolution")
    return {
        "complete": complete,
        "confirmed_hypotheses": [_summarize_node(node) for node in supported],
        "alternatives_open": alternatives,
        "blocking_questions": blocking_questions,
        "blockers": blockers,
    }


def evaluate_case(case: dict[str, Any], case_id: str, summary: str = "") -> dict[str, Any]:
    completion = _completion_signal(case)
    coverage_status = _coverage_status_from_case(case)
    passes = completion["complete"] and coverage_status["complete"]
    return {
        "case_id": case_id,
        "status": "passes" if passes else "fails",
        "summary": summary,
        "completion": completion,
        "coverage": coverage_status,
        "evaluated_at": utc_now(),
    }


def gate_from_case(case: dict[str, Any], case_id: str, summary: str = "completion gate") -> dict[str, Any]:
    current_proof = evaluate_case(case, case_id, summary)
    open_actions = [action for action in case.get("actions", []) if action.get("status") not in {"done", "cancelled"}]
    blockers = []
    if current_proof["status"] != "passes":
        blockers.append("proof does not pass")
        blockers.extend(current_proof.get("completion", {}).get("blockers", []))
        if not current_proof.get("coverage", {}).get("complete"):
            blockers.append("coverage is incomplete")
    if open_actions:
        blockers.append(f"{len(open_actions)} open action(s)")
    return {"case_id": case_id, "allowed": current_proof["status"] == "passes" and not open_actions, "blockers": blockers, "current_proof": current_proof}


def evaluate(workspace: str | Path | None, case_id: str, summary: str = "") -> dict[str, Any]:
    require_text(summary or "manual proof evaluation", "summary")

    def op(case: dict[str, Any]) -> dict[str, Any]:
        proof = {"id": new_id("proof"), **evaluate_case(case, case_id, summary)}
        case.setdefault("proofs", []).append(proof)
        return proof

    return store.mutate_case(workspace, case_id, op, lambda proof: {"type": "proof_evaluated", "case_id": case_id, "proof_id": proof["id"], "status": proof["status"]})


def completion_gate(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    return gate_from_case(case, case_id)


def close_case(workspace: str | Path | None, case_id: str, summary: str, approved_by: str = "system", force: bool = False) -> dict[str, Any]:
    summary = require_text(summary, "summary")
    approved_by = require_text(approved_by, "approved_by")

    def op(case: dict[str, Any]) -> dict[str, Any]:
        gate = gate_from_case(case, case_id, "closure gate")
        if not gate["allowed"] and not force:
            raise ValueError("Completion gate blocks closure: " + "; ".join(gate["blockers"]))
        case["status"] = validate_choice("closed", CASE_STATUSES, "case status")
        case["closure"] = {"closed_at": utc_now(), "summary": summary, "approved_by": approved_by, "forced": force, "gate": gate}
        return {"case_id": case_id, "status": case["status"], "closure": case["closure"]}

    return store.mutate_case(workspace, case_id, op, lambda result: {"type": "case_closed", "case_id": case_id, "forced": force})
