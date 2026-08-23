import fcntl
import json
import os
import re
import tempfile
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .ids import slugify, utc_now
from .models import EDGE_TYPES, NODE_STATUSES, NODE_TYPES, SCHEMA_VERSION, SOURCES, clamp_confidence, make_case, make_edge, make_node
from .validation import positive_limit, require_text, validate_choice, validate_metadata


class RevisionConflictError(RuntimeError):
    pass


class ClosedCaseError(RuntimeError):
    pass


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


def lock_file(workspace: str | Path | None, case_id: str) -> Path:
    return case_dir(workspace, case_id) / ".case.lock"


def events_file(workspace: str | Path | None, case_id: str) -> Path:
    return case_dir(workspace, case_id) / "events.jsonl"


def _read_case_path(path: Path) -> dict[str, Any]:
    case = json.loads(path.read_text(encoding="utf-8"))
    schema = case.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise ValueError(f"Unsupported Detective case schema: {schema!r}; expected {SCHEMA_VERSION}")
    return case


def _atomic_write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _locked(workspace: str | Path | None, case_id: str, callback: Callable[[], Any]) -> Any:
    directory = case_dir(workspace, case_id)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = lock_file(workspace, case_id)
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            return callback()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_event(workspace: str | Path | None, case_id: str, event: dict[str, Any]) -> None:
    event_record = {"timestamp": utc_now(), **event}
    path = events_file(workspace, case_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(json.dumps(event_record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def list_events(workspace: str | Path | None, case_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    limit = positive_limit(limit)
    path = events_file(workspace, case_id)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        try:
            if limit is None:
                return [json.loads(line) for line in handle if line.strip()]
            records: deque[dict[str, Any]] = deque(maxlen=limit)
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
            return list(records)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_case(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    path = case_file(workspace, case_id)
    if not path.exists():
        raise FileNotFoundError(f"Case not found: {case_id} at {path}")
    return _read_case_path(path)


def _ensure_mutable(case: dict[str, Any]) -> None:
    if case.get("status") == "closed":
        raise ClosedCaseError(f"Case is closed and cannot be mutated: {case['id']}")


def save_case(
    workspace: str | Path | None,
    case: dict[str, Any],
    event: dict[str, Any] | None = None,
    expected_revision: int | None = None,
    *,
    allow_closed: bool = False,
) -> dict[str, str]:
    validate_case_id(case["id"])

    def write() -> dict[str, str]:
        path = case_file(workspace, case["id"])
        current_revision = None
        if path.exists():
            current = _read_case_path(path)
            if not allow_closed:
                _ensure_mutable(current)
            current_revision = current.get("revision", 0)
        if expected_revision is not None and current_revision is not None and current_revision != expected_revision:
            raise RevisionConflictError(
                f"Revision conflict for {case['id']}: expected {expected_revision}, current {current_revision}"
            )
        stored = dict(case)
        if not allow_closed:
            _ensure_mutable(stored)
        base_revision = current_revision if current_revision is not None else int(stored.get("revision", 0))
        stored["revision"] = base_revision + 1
        stored["updated_at"] = utc_now()
        _atomic_write_json(path, stored)
        stored_id = stored["id"]
        case.clear()
        case.update(stored)
        if event:
            append_event(workspace, stored_id, event)
        return {"case_id": stored_id, "case_path": str(path), "status": "saved"}

    return _locked(workspace, case["id"], write)


def mutate_case(
    workspace: str | Path | None,
    case_id: str,
    mutator: Callable[[dict[str, Any]], Any],
    event_factory: Callable[[Any], dict[str, Any] | None] | None = None,
    expected_revision: int | None = None,
    *,
    allow_closed: bool = False,
) -> Any:
    def run() -> Any:
        path = case_file(workspace, case_id)
        if not path.exists():
            raise FileNotFoundError(f"Case not found: {case_id} at {path}")
        case = _read_case_path(path)
        if not allow_closed:
            _ensure_mutable(case)
        current_revision = int(case.get("revision", 0))
        if expected_revision is not None and current_revision != expected_revision:
            raise RevisionConflictError(f"Revision conflict for {case_id}: expected {expected_revision}, current {current_revision}")
        result = mutator(case)
        case["revision"] = current_revision + 1
        case["updated_at"] = utc_now()
        _atomic_write_json(path, case)
        event = event_factory(result) if event_factory else None
        if event:
            append_event(workspace, case_id, event)
        return result

    return _locked(workspace, case_id, run)


def open_case(
    workspace: str | Path | None,
    title: str,
    description: str,
    case_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    resolved_case_id = validate_case_id(case_id or slugify(title))

    def create() -> dict[str, str]:
        path = case_file(workspace, resolved_case_id)
        if path.exists():
            raise FileExistsError(f"Case already exists: {resolved_case_id} at {path}")
        case = make_case(resolved_case_id, title, description, config)
        case["revision"] = 1
        case["updated_at"] = utc_now()
        _atomic_write_json(path, case)
        append_event(workspace, resolved_case_id, {"type": "case_opened", "case_id": resolved_case_id})
        return {"case_id": resolved_case_id, "case_path": str(path)}

    return _locked(workspace, resolved_case_id, create)


def get_case_status(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = load_case(workspace, case_id)
    return {
        "case_id": case["id"],
        "status": case.get("status", "open"),
        "schema_version": case.get("schema_version"),
        "revision": case.get("revision", 0),
        "phase": case.get("ooda", {}).get("phase"),
        "closed_at": case.get("closure", {}).get("closed_at"),
    }


def find_by_id(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    for item in items:
        if item["id"] == item_id:
            return item
    raise KeyError(f"{label} not found: {item_id}")


def find_node(case: dict[str, Any], node_id: str) -> dict[str, Any]:
    return find_by_id(case["nodes"], node_id, "Node")


def find_edge(case: dict[str, Any], edge_id: str) -> dict[str, Any]:
    return find_by_id(case["edges"], edge_id, "Edge")


def merge_metadata(item: dict[str, Any], metadata: dict[str, Any] | None) -> None:
    if metadata is not None:
        merged = dict(item.get("metadata", {}))
        merged.update(validate_metadata(metadata))
        item["metadata"] = merged


def make_validated_node(
    node_type: str,
    content: str,
    status: str = "open",
    confidence: float = 0.5,
    source: str = "system",
    tags: list[str] | None = None,
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a node using the public store argument order and validation."""
    return make_node(
        validate_choice(node_type, NODE_TYPES, "node type"),
        require_text(content, "content"),
        validate_choice(status, NODE_STATUSES, "node status"),
        clamp_confidence(confidence),
        validate_choice(source, SOURCES, "source"),
        tags,
        created_by,
        validate_metadata(metadata),
    )


def add_node(workspace: str | Path | None, case_id: str, node_type: str, content: str, status: str = "open", confidence: float = 0.5, source: str = "system", tags: list[str] | None = None, created_by: str = "system", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        node = make_validated_node(node_type, content, status, confidence, source, tags, created_by, metadata)
        case["nodes"].append(node)
        return node
    return mutate_case(workspace, case_id, op, lambda node: {"type": "node_added", "case_id": case_id, "node_id": node["id"]})


def update_node(workspace: str | Path | None, case_id: str, node_id: str, content: str | None = None, status: str | None = None, confidence: float | None = None, tags: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        node = find_node(case, node_id)
        if content is not None:
            node["content"] = require_text(content, "content")
        if status is not None:
            node["status"] = validate_choice(status, NODE_STATUSES, "node status")
        if confidence is not None:
            node["confidence"] = clamp_confidence(confidence)
        if tags is not None:
            node["tags"] = tags
        merge_metadata(node, metadata)
        node["updated_at"] = utc_now()
        return node
    return mutate_case(workspace, case_id, op, lambda node: {"type": "node_updated", "case_id": case_id, "node_id": node_id})


def delete_node(workspace: str | Path | None, case_id: str, node_id: str) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        node = find_node(case, node_id)
        remaining_edges = [edge for edge in case["edges"] if edge["from_id"] != node_id and edge["to_id"] != node_id]
        removed_edges = len(case["edges"]) - len(remaining_edges)
        case["nodes"] = [existing for existing in case["nodes"] if existing["id"] != node_id]
        case["edges"] = remaining_edges
        return {**node, "_removed_edges": removed_edges}
    return mutate_case(workspace, case_id, op, lambda node: {"type": "node_deleted", "case_id": case_id, "node_id": node_id, "removed_edges": node.get("_removed_edges", 0)})


def add_edge(workspace: str | Path | None, case_id: str, from_id: str, to_id: str, edge_type: str, confidence: float = 0.5, rationale: str = "", created_by: str = "system", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        find_node(case, from_id)
        find_node(case, to_id)
        edge = make_edge(from_id, to_id, edge_type, confidence, rationale, created_by, metadata)
        case["edges"].append(edge)
        return edge
    return mutate_case(workspace, case_id, op, lambda edge: {"type": "edge_added", "case_id": case_id, "edge_id": edge["id"]})


def update_edge(workspace: str | Path | None, case_id: str, edge_id: str, edge_type: str | None = None, confidence: float | None = None, rationale: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        edge = find_edge(case, edge_id)
        if edge_type is not None:
            edge["type"] = validate_choice(edge_type, EDGE_TYPES, "edge type")
        if confidence is not None:
            edge["confidence"] = clamp_confidence(confidence)
        if rationale is not None:
            edge["rationale"] = require_text(rationale, "rationale")
        merge_metadata(edge, metadata)
        edge["updated_at"] = utc_now()
        return edge
    return mutate_case(workspace, case_id, op, lambda edge: {"type": "edge_updated", "case_id": case_id, "edge_id": edge_id})


def delete_edge(workspace: str | Path | None, case_id: str, edge_id: str) -> dict[str, Any]:
    def op(case: dict[str, Any]) -> dict[str, Any]:
        edge = find_edge(case, edge_id)
        case["edges"] = [existing for existing in case["edges"] if existing["id"] != edge_id]
        return edge
    return mutate_case(workspace, case_id, op, lambda edge: {"type": "edge_deleted", "case_id": case_id, "edge_id": edge_id})
