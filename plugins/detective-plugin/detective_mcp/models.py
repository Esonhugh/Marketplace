from copy import deepcopy
from typing import Any

from .ids import new_id, utc_now

NODE_TYPES = {
    "observation",
    "clue",
    "evidence",
    "hypothesis",
    "constraint",
    "conclusion",
    "question",
    "task",
}

NODE_STATUSES = {"open", "verified", "rejected", "stale", "resolved"}

EDGE_TYPES = {
    "supports",
    "contradicts",
    "derives",
    "requires",
    "eliminates",
    "related_to",
}

SOURCES = {"user", "agent", "tool", "file", "web", "mcp", "system"}

DEFAULT_CONFIG = {
    "autonomy": "full_auto",
    "checkpoint_interval": 5,
    "max_actions": 50,
    "user_override_policy": "always_priority",
    "deadlock_score_threshold": 0.3,
    "confidence_threshold_confirm": 0.85,
    "confidence_threshold_eliminate": 0.15,
}


def validate_choice(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"Invalid {field}: {value}. Allowed: {allowed_values}")
    return value


def clamp_confidence(value: float | int) -> float:
    numeric = float(value)
    if numeric < 0.0 or numeric > 1.0:
        raise ValueError(f"confidence must be between 0.0 and 1.0, got {value}")
    return numeric


def make_case(case_id: str, title: str, description: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    now = utc_now()
    merged_config = deepcopy(DEFAULT_CONFIG)
    if config:
        merged_config.update(config)
    return {
        "schema_version": "2.0",
        "id": case_id,
        "title": title,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "config": merged_config,
        "scheduler": {
            "attempted_directions": [],
            "next_actions": [],
        },
        "nodes": [],
        "edges": [],
        "actions": [],
    }


def make_node(
    node_type: str,
    content: str,
    status: str = "open",
    confidence: float = 0.5,
    source: str = "system",
    tags: list[str] | None = None,
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": new_id("n"),
        "type": validate_choice(node_type, NODE_TYPES, "node type"),
        "status": validate_choice(status, NODE_STATUSES, "node status"),
        "content": content,
        "confidence": clamp_confidence(confidence),
        "source": validate_choice(source, SOURCES, "source"),
        "tags": tags or [],
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "metadata": metadata or {},
    }


def make_edge(
    from_id: str,
    to_id: str,
    edge_type: str,
    confidence: float = 0.5,
    rationale: str = "",
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": new_id("e"),
        "from_id": from_id,
        "to_id": to_id,
        "type": validate_choice(edge_type, EDGE_TYPES, "edge type"),
        "confidence": clamp_confidence(confidence),
        "rationale": rationale,
        "created_by": created_by,
        "created_at": utc_now(),
        "metadata": metadata or {},
    }
