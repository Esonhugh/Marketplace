from pathlib import Path
from typing import Any

from . import store
from .ids import new_id, utc_now


def ensure_scheduler(case: dict[str, Any]) -> dict[str, Any]:
    scheduler = case.setdefault("scheduler", {})
    scheduler.setdefault("attempted_directions", [])
    scheduler.setdefault("next_actions", [])
    return scheduler



def _same_direction(direction: dict[str, Any], description: str, target_node_ids: list[str]) -> bool:
    return direction.get("description") == description and sorted(direction.get("target_node_ids", [])) == sorted(target_node_ids)



def record_direction_attempt(
    workspace: str | Path | None,
    case_id: str,
    description: str,
    target_node_ids: list[str],
    new_evidence_count: int,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    scheduler = ensure_scheduler(case)
    normalized_target_ids = sorted(target_node_ids)

    direction = next(
        (
            existing
            for existing in scheduler["attempted_directions"]
            if _same_direction(existing, description, normalized_target_ids)
        ),
        None,
    )

    if direction is None:
        direction = {
            "id": new_id("direction"),
            "description": description,
            "target_node_ids": normalized_target_ids,
            "attempts": 0,
            "status": "open",
            "created_at": utc_now(),
        }
        scheduler["attempted_directions"].append(direction)

    direction["attempts"] += 1
    direction["target_node_ids"] = normalized_target_ids
    direction["new_evidence_count"] = int(direction.get("new_evidence_count", 0)) + int(new_evidence_count)
    direction["last_attempted_at"] = utc_now()
    direction["status"] = "cold" if direction["attempts"] >= 3 and direction["new_evidence_count"] == 0 else "open"

    store.save_case(
        workspace,
        case,
        event={"type": "direction_attempted", "case_id": case_id, "direction_id": direction["id"]},
    )
    return direction



def add_next_action(
    workspace: str | Path | None,
    case_id: str,
    description: str,
    assigned_role: str,
    priority: float,
    reason: str,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    scheduler = ensure_scheduler(case)
    action = {
        "id": new_id("action"),
        "description": description,
        "assigned_role": assigned_role,
        "priority": float(priority),
        "reason": reason,
        "status": "pending",
        "created_at": utc_now(),
    }
    scheduler["next_actions"].append(action)
    scheduler["next_actions"].sort(key=lambda existing: existing["priority"], reverse=True)

    store.save_case(
        workspace,
        case,
        event={"type": "next_action_added", "case_id": case_id, "next_action_id": action["id"]},
    )
    return action



def _matching_cold_direction(
    case_scheduler: dict[str, Any],
    description: str,
    target_node_ids: list[str],
) -> dict[str, Any] | None:
    normalized_target_ids = sorted(target_node_ids)
    return next(
        (
            direction
            for direction in case_scheduler.get("attempted_directions", [])
            if direction.get("status") == "cold" and _same_direction(direction, description, normalized_target_ids)
        ),
        None,
    )



def score_candidate_actions(
    workspace: str | Path | None,
    case_id: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case = store.load_case(workspace, case_id)
    case_scheduler = ensure_scheduler(case)
    scored = []

    for candidate in candidates:
        information_gain = float(candidate.get("information_gain", 0.5))
        feasibility = float(candidate.get("feasibility", 0.5))
        urgency = float(candidate.get("urgency", 0.5))
        normalized_cost = max(float(candidate.get("cost", 5)), 0.1)
        cold_direction = _matching_cold_direction(
            case_scheduler,
            candidate.get("description", ""),
            list(candidate.get("target_node_ids", [])),
        ) is not None
        score = (information_gain * feasibility * urgency) / normalized_cost
        if cold_direction:
            score *= 0.1
        scored.append({
            **candidate,
            "score": round(score, 4),
            "cold_direction": cold_direction,
        })

    scored.sort(key=lambda existing: existing["score"], reverse=True)
    return scored



def apply_user_guidance(
    workspace: str | Path | None,
    case_id: str,
    guidance_type: str,
    content: str,
) -> dict[str, Any]:
    node_type_by_guidance = {
        "fact": "evidence",
        "theory": "hypothesis",
        "constraint": "constraint",
        "question": "question",
    }
    node_type = node_type_by_guidance.get(guidance_type, "observation")
    confidence = 1.0 if node_type in {"evidence", "constraint"} else 0.8
    node = store.add_node(
        workspace,
        case_id,
        node_type,
        content,
        confidence=confidence,
        source="user",
        tags=["user-guidance"],
        created_by="user",
        metadata={
            "user_override": True,
            "guidance_type": guidance_type,
        },
    )
    return {
        "case_id": case_id,
        "node": node,
        "policy": "user_guidance_has_priority",
    }
