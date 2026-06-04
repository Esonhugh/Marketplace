import json
import os
import re
from pathlib import Path
from typing import Any

from .ids import slugify, utc_now
from .models import EDGE_TYPES, NODE_STATUSES, clamp_confidence, make_case, make_edge, make_node, validate_choice


def workspace_root(workspace: str | Path | None = None) -> Path:
    if workspace is not None:
        return Path(workspace).expanduser().resolve()
    env_workspace = os.environ.get("DETECTIVE_WORKSPACE")
    if env_workspace:
        return Path(env_workspace).expanduser().resolve()
    return Path.cwd().resolve()


CASE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def cases_root(workspace: str | Path | None = None) -> Path:
    return workspace_root(workspace) / ".detective" / "cases"


def validate_case_id(case_id: str) -> str:
    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise ValueError(f"Invalid case_id: {case_id}. Use slug-safe lowercase letters, digits, and hyphens.")
    return case_id


def case_dir(workspace: str | Path | None, case_id: str) -> Path:
    safe_case_id = validate_case_id(case_id)
    root = cases_root(workspace).resolve()
    path = (root / safe_case_id).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Invalid case_id: {case_id}. Case path escapes cases root.")
    return path


def case_file(workspace: str | Path | None, case_id: str) -> Path:
    return case_dir(workspace, case_id) / "case.json"


def events_file(workspace: str | Path | None, case_id: str) -> Path:
    return case_dir(workspace, case_id) / "events.jsonl"


def open_case(
    workspace: str | Path | None,
    title: str,
    description: str,
    case_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    resolved_case_id = validate_case_id(case_id or slugify(title))
    path = case_file(workspace, resolved_case_id)
    if path.exists():
        raise FileExistsError(f"Case already exists: {resolved_case_id} at {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    case = make_case(resolved_case_id, title, description, config)
    save_case(workspace, case, event={"type": "case_opened", "case_id": resolved_case_id})
    return {
        "case_id": resolved_case_id,
        "case_path": str(path),
    }


def load_case(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    path = case_file(workspace, case_id)
    if not path.exists():
        raise FileNotFoundError(f"Case not found: {case_id} at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_case(workspace: str | Path | None, case: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, str]:
    validate_case_id(case["id"])
    case["updated_at"] = utc_now()
    directory = case_dir(workspace, case["id"])
    directory.mkdir(parents=True, exist_ok=True)
    path = case_file(workspace, case["id"])
    path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if event:
        append_event(workspace, case["id"], event)
    return {"case_id": case["id"], "case_path": str(path), "status": "saved"}


def append_event(workspace: str | Path | None, case_id: str, event: dict[str, Any]) -> None:
    event_record = {"timestamp": utc_now(), **event}
    path = events_file(workspace, case_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event_record, ensure_ascii=False) + "\n")


def find_node(case: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in case["nodes"]:
        if node["id"] == node_id:
            return node
    raise KeyError(f"Node not found: {node_id}")


def find_edge(case: dict[str, Any], edge_id: str) -> dict[str, Any]:
    for edge in case["edges"]:
        if edge["id"] == edge_id:
            return edge
    raise KeyError(f"Edge not found: {edge_id}")


def add_node(
    workspace: str | Path | None,
    case_id: str,
    node_type: str,
    content: str,
    status: str = "open",
    confidence: float = 0.5,
    source: str = "system",
    tags: list[str] | None = None,
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    node = make_node(node_type, content, status, confidence, source, tags, created_by, metadata)
    case["nodes"].append(node)
    save_case(workspace, case, event={"type": "node_added", "case_id": case_id, "node_id": node["id"]})
    return node


def update_node(
    workspace: str | Path | None,
    case_id: str,
    node_id: str,
    content: str | None = None,
    status: str | None = None,
    confidence: float | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    node = find_node(case, node_id)
    if content is not None:
        node["content"] = content
    if status is not None:
        node["status"] = validate_choice(status, NODE_STATUSES, "node status")
    if confidence is not None:
        node["confidence"] = clamp_confidence(confidence)
    if tags is not None:
        node["tags"] = tags
    if metadata is not None:
        merged = dict(node.get("metadata", {}))
        merged.update(metadata)
        node["metadata"] = merged
    node["updated_at"] = utc_now()
    save_case(workspace, case, event={"type": "node_updated", "case_id": case_id, "node_id": node_id})
    return node


def delete_node(workspace: str | Path | None, case_id: str, node_id: str) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    node = find_node(case, node_id)
    remaining_nodes = [existing for existing in case["nodes"] if existing["id"] != node_id]
    remaining_edges = [edge for edge in case["edges"] if edge["from_id"] != node_id and edge["to_id"] != node_id]
    removed_edges = len(case["edges"]) - len(remaining_edges)
    case["nodes"] = remaining_nodes
    case["edges"] = remaining_edges
    save_case(
        workspace,
        case,
        event={"type": "node_deleted", "case_id": case_id, "node_id": node_id, "removed_edges": removed_edges},
    )
    return node


def add_edge(
    workspace: str | Path | None,
    case_id: str,
    from_id: str,
    to_id: str,
    edge_type: str,
    confidence: float = 0.5,
    rationale: str = "",
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    find_node(case, from_id)
    find_node(case, to_id)
    edge = make_edge(from_id, to_id, edge_type, confidence, rationale, created_by, metadata)
    case["edges"].append(edge)
    save_case(workspace, case, event={"type": "edge_added", "case_id": case_id, "edge_id": edge["id"]})
    return edge


def update_edge(
    workspace: str | Path | None,
    case_id: str,
    edge_id: str,
    edge_type: str | None = None,
    confidence: float | None = None,
    rationale: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    edge = find_edge(case, edge_id)
    if edge_type is not None:
        edge["type"] = validate_choice(edge_type, EDGE_TYPES, "edge type")
    if confidence is not None:
        edge["confidence"] = clamp_confidence(confidence)
    if rationale is not None:
        edge["rationale"] = rationale
    if metadata is not None:
        merged = dict(edge.get("metadata", {}))
        merged.update(metadata)
        edge["metadata"] = merged
    edge["updated_at"] = utc_now()
    save_case(workspace, case, event={"type": "edge_updated", "case_id": case_id, "edge_id": edge_id})
    return edge


def delete_edge(workspace: str | Path | None, case_id: str, edge_id: str) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    edge = find_edge(case, edge_id)
    case["edges"] = [existing for existing in case["edges"] if existing["id"] != edge_id]
    save_case(workspace, case, event={"type": "edge_deleted", "case_id": case_id, "edge_id": edge_id})
    return edge
