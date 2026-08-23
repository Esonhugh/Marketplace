from pathlib import Path
from typing import Any

from . import store
from .ids import new_id, utc_now
from .models import OODA_PHASES
from .validation import require_text, validate_choice, validate_metadata

INTENT_STATUSES = {"open", "resolved", "cancelled"}


def transition_phase(workspace: str | Path | None, case_id: str, phase: str, reason: str = "", session: str | None = None) -> dict[str, Any]:
    phase = validate_choice(phase, OODA_PHASES, "OODA phase")
    reason = require_text(reason or "phase transition", "reason")

    def op(case: dict[str, Any]) -> dict[str, Any]:
        ooda = case.setdefault("ooda", {"session": None, "phase": "observe", "intents": []})
        previous = ooda.get("phase", "observe")
        if session is not None:
            ooda["session"] = session
        elif ooda.get("session") is None:
            ooda["session"] = new_id("ooda")
        ooda["phase"] = phase
        ooda["updated_at"] = utc_now()
        result = {"case_id": case_id, "session": ooda["session"], "previous_phase": previous, "phase": phase, "reason": reason}
        case.setdefault("checkpoints", []).append({"id": new_id("checkpoint"), "kind": "phase_transition", **result, "created_at": utc_now()})
        return result

    return store.mutate_case(workspace, case_id, op, lambda result: {"type": "ooda_phase_transition", **result})


def add_intent(workspace: str | Path | None, case_id: str, intent: str, phase: str | None = None, created_by: str = "system", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    intent = require_text(intent, "intent")
    metadata = validate_metadata(metadata)

    def op(case: dict[str, Any]) -> dict[str, Any]:
        ooda = case.setdefault("ooda", {"session": None, "phase": "observe", "intents": []})
        actual_phase = validate_choice(phase or ooda.get("phase", "observe"), OODA_PHASES, "OODA phase")
        item = {"id": new_id("intent"), "intent": intent, "phase": actual_phase, "status": "open", "created_by": created_by, "created_at": utc_now(), "updated_at": utc_now(), "metadata": metadata}
        ooda.setdefault("intents", []).append(item)
        return item

    return store.mutate_case(workspace, case_id, op, lambda item: {"type": "intent_added", "case_id": case_id, "intent_id": item["id"]})


def list_intents(workspace: str | Path | None, case_id: str, phase: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    if phase is not None:
        validate_choice(phase, OODA_PHASES, "OODA phase")
    if status is not None:
        validate_choice(status, INTENT_STATUSES, "intent status")
    case = store.load_case(workspace, case_id)
    intents = case.get("ooda", {}).get("intents", [])
    if phase is not None:
        intents = [item for item in intents if item.get("phase") == phase]
    if status is not None:
        intents = [item for item in intents if item.get("status") == status]
    return intents
