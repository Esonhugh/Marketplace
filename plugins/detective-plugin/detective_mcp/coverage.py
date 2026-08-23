from pathlib import Path
from typing import Any

from . import store
from .ids import new_id, utc_now
from .models import COVERAGE_STATUSES
from .validation import require_text, validate_choice


def add_item(workspace: str | Path | None, case_id: str, area: str, status: str = "planned", notes: str = "") -> dict[str, Any]:
    area = require_text(area, "area")
    status = validate_choice(status, COVERAGE_STATUSES, "coverage status")

    def op(case: dict[str, Any]) -> dict[str, Any]:
        item = {"id": new_id("coverage"), "area": area, "status": status, "notes": notes, "created_at": utc_now(), "updated_at": utc_now()}
        case.setdefault("coverage", []).append(item)
        return item

    return store.mutate_case(workspace, case_id, op, lambda item: {"type": "coverage_added", "case_id": case_id, "coverage_id": item["id"]})


def update_item(workspace: str | Path | None, case_id: str, coverage_id: str, status: str | None = None, notes: str | None = None) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        item = store.find_by_id(case.setdefault("coverage", []), coverage_id, "Coverage item")
        if status is not None:
            item["status"] = validate_choice(status, COVERAGE_STATUSES, "coverage status")
        if notes is not None:
            item["notes"] = notes
        item["updated_at"] = utc_now()
        return item

    return store.mutate_case(workspace, case_id, op, lambda item: {"type": "coverage_updated", "case_id": case_id, "coverage_id": coverage_id})


def status_from_case(case: dict[str, Any]) -> dict[str, Any]:
    items = case.get("coverage", [])
    counts: dict[str, int] = {}
    for item in items:
        counts[item.get("status", "unknown")] = counts.get(item.get("status", "unknown"), 0) + 1
    incomplete = [item for item in items if item.get("status") != "complete"]
    return {"case_id": case["id"], "total": len(items), "counts": counts, "complete": bool(items) and not incomplete, "incomplete": incomplete}


def status(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    return status_from_case(store.load_case(workspace, case_id))
