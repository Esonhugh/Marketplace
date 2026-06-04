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
