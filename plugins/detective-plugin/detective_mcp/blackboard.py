from pathlib import Path
from typing import Any

from . import store
from .ids import new_id, utc_now
from .models import BLACKBOARD_STATUSES
from .validation import require_text, validate_choice


def add_entry(workspace: str | Path | None, case_id: str, content: str, kind: str = "note", tags: list[str] | None = None, created_by: str = "system") -> dict[str, Any]:
    content = require_text(content, "content")
    kind = require_text(kind, "kind")

    def op(case: dict[str, Any]) -> dict[str, Any]:
        entry = {"id": new_id("bb"), "kind": kind, "content": content, "status": "active", "tags": tags or [], "created_by": created_by, "created_at": utc_now(), "updated_at": utc_now()}
        case.setdefault("blackboard", []).append(entry)
        return entry

    return store.mutate_case(workspace, case_id, op, lambda entry: {"type": "blackboard_added", "case_id": case_id, "entry_id": entry["id"]})


def list_entries(workspace: str | Path | None, case_id: str, status: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    if status is not None:
        validate_choice(status, BLACKBOARD_STATUSES, "blackboard status")
    case = store.load_case(workspace, case_id)
    entries = case.get("blackboard", [])
    if status is not None:
        entries = [entry for entry in entries if entry.get("status") == status]
    if kind is not None:
        entries = [entry for entry in entries if entry.get("kind") == kind]
    return entries


def update_entry(workspace: str | Path | None, case_id: str, entry_id: str, content: str | None = None, status: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        entry = store.find_by_id(case.setdefault("blackboard", []), entry_id, "Blackboard entry")
        if content is not None:
            entry["content"] = require_text(content, "content")
        if status is not None:
            entry["status"] = validate_choice(status, BLACKBOARD_STATUSES, "blackboard status")
        if tags is not None:
            entry["tags"] = tags
        entry["updated_at"] = utc_now()
        return entry

    return store.mutate_case(workspace, case_id, op, lambda entry: {"type": "blackboard_updated", "case_id": case_id, "entry_id": entry_id})


def promote_entry(workspace: str | Path | None, case_id: str, entry_id: str, node_type: str = "observation", confidence: float = 0.6) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        entry = store.find_by_id(case.setdefault("blackboard", []), entry_id, "Blackboard entry")
        existing = next((node for node in case["nodes"] if node.get("metadata", {}).get("blackboard_entry_id") == entry_id), None)
        if existing is None:
            existing = store.make_validated_node(
                node_type,
                entry["content"],
                status="open",
                confidence=confidence,
                source="system",
                tags=entry.get("tags", []) + ["from-blackboard"],
                metadata={"blackboard_entry_id": entry_id},
            )
            case["nodes"].append(existing)
        entry["status"] = "promoted"
        entry["promoted_node_id"] = existing["id"]
        entry["updated_at"] = utc_now()
        return {"entry": entry, "node": existing}

    return store.mutate_case(workspace, case_id, op, lambda result: {"type": "blackboard_promoted", "case_id": case_id, "entry_id": entry_id, "node_id": result["node"]["id"]})
