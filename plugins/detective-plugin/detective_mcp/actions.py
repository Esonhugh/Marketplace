from pathlib import Path
from typing import Any

from . import store
from .ids import new_id, utc_now
from .models import ACTION_STATUSES
from .validation import finite_float, require_text, validate_choice, validate_metadata


def add_action(workspace: str | Path | None, case_id: str, description: str, assigned_role: str = "agent", priority: float = 0.5, reason: str = "") -> dict[str, Any]:
    description = require_text(description, "description")
    assigned_role = require_text(assigned_role, "assigned_role")
    priority_value = finite_float(priority, "priority", 0.0, 1.0)

    def op(case: dict[str, Any]) -> dict[str, Any]:
        max_actions = int(case.get("config", {}).get("max_actions", 50))
        if len(case.setdefault("actions", [])) >= max_actions:
            raise ValueError(f"max_actions reached for case {case_id}: {max_actions}")
        action = {"id": new_id("action"), "description": description, "assigned_role": assigned_role, "priority": priority_value, "reason": reason, "status": "pending", "checkpoints": [], "created_at": utc_now(), "updated_at": utc_now()}
        case["actions"].append(action)
        return action

    return store.mutate_case(workspace, case_id, op, lambda action: {"type": "action_added", "case_id": case_id, "action_id": action["id"]})


def update_action(workspace: str | Path | None, case_id: str, action_id: str, status: str | None = None, result: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = validate_metadata(metadata) if metadata is not None else None

    def op(case: dict[str, Any]) -> dict[str, Any]:
        action = store.find_by_id(case.setdefault("actions", []), action_id, "Action")
        if status is not None:
            action["status"] = validate_choice(status, ACTION_STATUSES, "action status")
        if result is not None:
            action["result"] = require_text(result, "result")
        store.merge_metadata(action, metadata)
        action["updated_at"] = utc_now()
        return action

    return store.mutate_case(workspace, case_id, op, lambda action: {"type": "action_updated", "case_id": case_id, "action_id": action_id})


def add_checkpoint(workspace: str | Path | None, case_id: str, summary: str, action_id: str | None = None, created_by: str = "system", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = require_text(summary, "summary")
    metadata = validate_metadata(metadata)

    def op(case: dict[str, Any]) -> dict[str, Any]:
        checkpoint = {"id": new_id("checkpoint"), "action_id": action_id, "summary": summary, "created_by": created_by, "created_at": utc_now(), "metadata": metadata}
        case.setdefault("checkpoints", []).append(checkpoint)
        if action_id:
            action = store.find_by_id(case.setdefault("actions", []), action_id, "Action")
            action.setdefault("checkpoints", []).append(checkpoint["id"])
            action["updated_at"] = utc_now()
        return checkpoint

    return store.mutate_case(workspace, case_id, op, lambda checkpoint: {"type": "checkpoint_added", "case_id": case_id, "checkpoint_id": checkpoint["id"]})


def list_actions(workspace: str | Path | None, case_id: str, status: str | None = None) -> list[dict[str, Any]]:
    if status is not None:
        validate_choice(status, ACTION_STATUSES, "action status")
    case = store.load_case(workspace, case_id)
    actions = case.get("actions", [])
    if status is not None:
        actions = [action for action in actions if action.get("status") == status]
    return actions
