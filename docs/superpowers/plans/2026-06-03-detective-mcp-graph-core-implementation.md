# Detective v2 MCP Graph Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python + uv stdio MCP server for `plugins/detective-plugin` that stores investigation graph state in `.detective/cases/<case-id>/case.json` and exposes typed tools for cases, nodes, edges, graph queries, and Markdown/Mermaid exports.

**Architecture:** Keep the existing v1 skills/scripts intact and add a v2 MCP graph core in parallel. The MCP server is a thin tool layer over focused pure-Python modules: `models.py` validates schema, `store.py` owns persistence and mutation, `graph.py` owns read/query algorithms, and `exports.py` generates Markdown/Mermaid projections. JSON is canonical; generated Markdown/Mermaid are derived artifacts.

**Tech Stack:** Python 3.11+, uv, `mcp` Python SDK with FastMCP, pytest, stdlib `dataclasses`, `json`, `pathlib`, `collections.deque`.

---

## Scope Check

This plan implements only Detective v2 MCP Graph Core. It intentionally excludes v2.1 autonomous investigation, scheduler memory, specialist agents, convergence/deadlock signals, and skill rewrites beyond README documentation.

## File Structure

Create or modify these files:

- Create: `plugins/detective-plugin/.mcp.json` — plugin MCP registration using uv.
- Create: `plugins/detective-plugin/pyproject.toml` — uv project metadata and dependencies.
- Create: `plugins/detective-plugin/detective_mcp/__init__.py` — package marker and version.
- Create: `plugins/detective-plugin/detective_mcp/ids.py` — UTC timestamps, stable slug generation, prefixed IDs.
- Create: `plugins/detective-plugin/detective_mcp/models.py` — Case/Node/Edge constructors and validation.
- Create: `plugins/detective-plugin/detective_mcp/store.py` — project-local `.detective/` persistence and mutation.
- Create: `plugins/detective-plugin/detective_mcp/graph.py` — overview, list/search, neighbors, shortest path.
- Create: `plugins/detective-plugin/detective_mcp/exports.py` — Markdown and Mermaid projections.
- Create: `plugins/detective-plugin/detective_mcp/server.py` — FastMCP tool definitions.
- Create: `plugins/detective-plugin/tests/test_config.py` — package/MCP config tests.
- Create: `plugins/detective-plugin/tests/test_store.py` — persistence and mutation tests.
- Create: `plugins/detective-plugin/tests/test_graph.py` — graph query tests.
- Create: `plugins/detective-plugin/tests/test_exports.py` — Markdown/Mermaid tests.
- Create: `plugins/detective-plugin/tests/test_server_tools.py` — tool wrapper smoke tests.
- Modify: `plugins/detective-plugin/README.md` — document v2 MCP tools and storage.
- Modify: `plugins/detective-plugin/README-zh.md` — add brief Chinese v2 MCP summary.
- Modify: `plugins/detective-plugin/.claude-plugin/plugin.json` — bump plugin version and mention MCP graph core.

## Task 1: Add uv project and MCP registration

**Files:**
- Create: `plugins/detective-plugin/tests/test_config.py`
- Create: `plugins/detective-plugin/pyproject.toml`
- Create: `plugins/detective-plugin/.mcp.json`
- Create: `plugins/detective-plugin/detective_mcp/__init__.py`

- [ ] **Step 1: Write the failing config test**

Create `plugins/detective-plugin/tests/test_config.py`:

```python
import json
from pathlib import Path


def test_pyproject_declares_mcp_dependency():
    text = Path("pyproject.toml").read_text()
    assert 'name = "detective-plugin"' in text
    assert '"mcp' in text
    assert '"pytest' in text


def test_mcp_json_uses_uv_and_plugin_root():
    config = json.loads(Path(".mcp.json").read_text())
    server = config["detective"]
    assert server["command"] == "uv"
    assert server["args"] == [
        "--directory",
        "${CLAUDE_PLUGIN_ROOT}",
        "run",
        "python",
        "-m",
        "detective_mcp.server",
    ]
    assert server["env"]["DETECTIVE_WORKSPACE"] == "${PWD}"


def test_package_imports():
    import detective_mcp

    assert detective_mcp.__version__ == "0.2.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `plugins/detective-plugin`:

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL because `pyproject.toml`, `.mcp.json`, or `detective_mcp` do not exist yet.

- [ ] **Step 3: Add uv project metadata**

Create `plugins/detective-plugin/pyproject.toml`:

```toml
[project]
name = "detective-plugin"
version = "0.2.0"
description = "Detective investigation graph MCP server for Claude Code"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: Add MCP registration**

Create `plugins/detective-plugin/.mcp.json`:

```json
{
  "detective": {
    "command": "uv",
    "args": [
      "--directory",
      "${CLAUDE_PLUGIN_ROOT}",
      "run",
      "python",
      "-m",
      "detective_mcp.server"
    ],
    "env": {
      "DETECTIVE_WORKSPACE": "${PWD}"
    }
  }
}
```

`DETECTIVE_WORKSPACE` gives the server a project-local storage root even though `uv --directory` runs from the plugin root.

- [ ] **Step 5: Add package marker**

Create `plugins/detective-plugin/detective_mcp/__init__.py`:

```python
__version__ = "0.2.0"
```

- [ ] **Step 6: Run config test**

Run:

```bash
uv run pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 7: Lock dependencies**

Run:

```bash
uv lock
```

Expected: `uv.lock` is created or updated.

- [ ] **Step 8: Commit checkpoint if commits are authorized**

If the user has authorized commits for this implementation, run:

```bash
git add plugins/detective-plugin/pyproject.toml plugins/detective-plugin/uv.lock plugins/detective-plugin/.mcp.json plugins/detective-plugin/detective_mcp/__init__.py plugins/detective-plugin/tests/test_config.py
git commit -m "feat: add detective MCP uv project"
```

## Task 2: Implement IDs, models, and case persistence

**Files:**
- Create: `plugins/detective-plugin/tests/test_store.py`
- Create: `plugins/detective-plugin/detective_mcp/ids.py`
- Create: `plugins/detective-plugin/detective_mcp/models.py`
- Create: `plugins/detective-plugin/detective_mcp/store.py`

- [ ] **Step 1: Write failing persistence tests**

Create `plugins/detective-plugin/tests/test_store.py`:

```python
import json
from pathlib import Path

import pytest

from detective_mcp import store


def test_open_case_creates_project_local_case(tmp_path):
    result = store.open_case(
        workspace=tmp_path,
        title="Investigate strange behavior",
        description="Something changed and the cause is unknown",
        case_id="strange-behavior",
    )

    assert result["case_id"] == "strange-behavior"
    case_path = tmp_path / ".detective" / "cases" / "strange-behavior" / "case.json"
    assert case_path.exists()

    data = json.loads(case_path.read_text())
    assert data["schema_version"] == "2.0"
    assert data["id"] == "strange-behavior"
    assert data["title"] == "Investigate strange behavior"
    assert data["config"]["autonomy"] == "full_auto"
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["actions"] == []


def test_open_case_generates_slug_when_case_id_missing(tmp_path):
    result = store.open_case(
        workspace=tmp_path,
        title="Config Drift? Maybe!",
        description="Check generated IDs",
    )

    assert result["case_id"] == "config-drift-maybe"
    assert (tmp_path / ".detective" / "cases" / "config-drift-maybe" / "case.json").exists()


def test_load_case_returns_existing_case(tmp_path):
    store.open_case(tmp_path, "A Case", "Description", case_id="a-case")

    loaded = store.load_case(tmp_path, "a-case")

    assert loaded["id"] == "a-case"
    assert loaded["title"] == "A Case"


def test_load_case_raises_for_missing_case(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing-case"):
        store.load_case(tmp_path, "missing-case")


def test_mutation_appends_event_log(tmp_path):
    store.open_case(tmp_path, "Event Case", "Description", case_id="event-case")
    case = store.load_case(tmp_path, "event-case")
    store.save_case(tmp_path, case, event={"type": "test_event", "message": "recorded"})

    events = tmp_path / ".detective" / "cases" / "event-case" / "events.jsonl"
    assert events.exists()
    line = events.read_text().strip()
    assert '"type": "test_event"' in line
    assert '"message": "recorded"' in line
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_store.py -v
```

Expected: FAIL because `ids.py`, `models.py`, and `store.py` are missing.

- [ ] **Step 3: Implement ID helpers**

Create `plugins/detective-plugin/detective_mcp/ids.py`:

```python
import re
import time
import uuid


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled-case"
```

- [ ] **Step 4: Implement model constructors and validation**

Create `plugins/detective-plugin/detective_mcp/models.py`:

```python
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
```

- [ ] **Step 5: Implement persistence**

Create `plugins/detective-plugin/detective_mcp/store.py`:

```python
import json
import os
from pathlib import Path
from typing import Any

from .ids import slugify, utc_now
from .models import EDGE_TYPES, NODE_STATUSES, NODE_TYPES, make_case, make_edge, make_node, validate_choice


def workspace_root(workspace: str | Path | None = None) -> Path:
    if workspace is not None:
        return Path(workspace).expanduser().resolve()
    env_workspace = os.environ.get("DETECTIVE_WORKSPACE")
    if env_workspace:
        return Path(env_workspace).expanduser().resolve()
    return Path.cwd().resolve()


def cases_root(workspace: str | Path | None = None) -> Path:
    return workspace_root(workspace) / ".detective" / "cases"


def case_dir(workspace: str | Path | None, case_id: str) -> Path:
    return cases_root(workspace) / case_id


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
    resolved_case_id = case_id or slugify(title)
    directory = case_dir(workspace, resolved_case_id)
    directory.mkdir(parents=True, exist_ok=True)
    case = make_case(resolved_case_id, title, description, config)
    save_case(workspace, case, event={"type": "case_opened", "case_id": resolved_case_id})
    return {
        "case_id": resolved_case_id,
        "case_path": str(case_file(workspace, resolved_case_id)),
    }


def load_case(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    path = case_file(workspace, case_id)
    if not path.exists():
        raise FileNotFoundError(f"Case not found: {case_id} at {path}")
    return json.loads(path.read_text())


def save_case(workspace: str | Path | None, case: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, str]:
    case["updated_at"] = utc_now()
    directory = case_dir(workspace, case["id"])
    directory.mkdir(parents=True, exist_ok=True)
    path = case_file(workspace, case["id"])
    path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n")
    if event:
        append_event(workspace, case["id"], event)
    return {"case_id": case["id"], "case_path": str(path), "status": "saved"}


def append_event(workspace: str | Path | None, case_id: str, event: dict[str, Any]) -> None:
    event_record = {"timestamp": utc_now(), **event}
    path = events_file(workspace, case_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(event_record, ensure_ascii=False) + "\n")


def find_node(case: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in case["nodes"]:
        if node["id"] == node_id:
            return node
    raise KeyError(f"Node not found: {node_id}")


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
        from .models import clamp_confidence

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
```

- [ ] **Step 6: Run persistence tests**

Run:

```bash
uv run pytest tests/test_store.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/ids.py plugins/detective-plugin/detective_mcp/models.py plugins/detective-plugin/detective_mcp/store.py plugins/detective-plugin/tests/test_store.py
git commit -m "feat: add detective case persistence"
```

## Task 3: Add node and edge mutation coverage

**Files:**
- Modify: `plugins/detective-plugin/tests/test_store.py`
- Modify: `plugins/detective-plugin/detective_mcp/store.py`

- [ ] **Step 1: Add failing mutation tests**

Append to `plugins/detective-plugin/tests/test_store.py`:

```python

def test_add_and_update_node_persists(tmp_path):
    store.open_case(tmp_path, "Node Case", "Description", case_id="node-case")

    node = store.add_node(
        tmp_path,
        "node-case",
        node_type="hypothesis",
        content="Configuration drift caused the issue",
        confidence=0.6,
        source="agent",
        tags=["config"],
        created_by="hypothesis-generator",
    )
    updated = store.update_node(
        tmp_path,
        "node-case",
        node["id"],
        status="verified",
        confidence=0.9,
        metadata={"reviewed": True},
    )

    loaded = store.load_case(tmp_path, "node-case")
    assert loaded["nodes"][0]["id"] == node["id"]
    assert updated["status"] == "verified"
    assert updated["confidence"] == 0.9
    assert updated["metadata"]["reviewed"] is True


def test_add_edge_requires_existing_nodes(tmp_path):
    store.open_case(tmp_path, "Edge Case", "Description", case_id="edge-case")
    observation = store.add_node(tmp_path, "edge-case", "observation", "A fact", source="user")
    hypothesis = store.add_node(tmp_path, "edge-case", "hypothesis", "An explanation", source="agent")

    edge = store.add_edge(
        tmp_path,
        "edge-case",
        from_id=observation["id"],
        to_id=hypothesis["id"],
        edge_type="supports",
        rationale="The fact supports the explanation",
    )

    loaded = store.load_case(tmp_path, "edge-case")
    assert loaded["edges"] == [edge]
    assert edge["type"] == "supports"


def test_add_edge_rejects_missing_endpoint(tmp_path):
    store.open_case(tmp_path, "Bad Edge", "Description", case_id="bad-edge")
    observation = store.add_node(tmp_path, "bad-edge", "observation", "A fact")

    with pytest.raises(KeyError, match="Node not found: missing-node"):
        store.add_edge(tmp_path, "bad-edge", observation["id"], "missing-node", "supports")


def test_validation_rejects_invalid_values(tmp_path):
    store.open_case(tmp_path, "Validation", "Description", case_id="validation")

    with pytest.raises(ValueError, match="Invalid node type"):
        store.add_node(tmp_path, "validation", "invalid", "Bad node")

    node_a = store.add_node(tmp_path, "validation", "observation", "A")
    node_b = store.add_node(tmp_path, "validation", "hypothesis", "B")
    with pytest.raises(ValueError, match="Invalid edge type"):
        store.add_edge(tmp_path, "validation", node_a["id"], node_b["id"], "blocks")
```

- [ ] **Step 2: Run mutation tests**

Run:

```bash
uv run pytest tests/test_store.py -v
```

Expected: PASS if Task 2 implementation is complete. If it fails, fix only `store.py` or `models.py` to satisfy these exact tests.

- [ ] **Step 3: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/store.py plugins/detective-plugin/tests/test_store.py
git commit -m "test: cover detective graph mutations"
```

## Task 4: Implement graph overview, listing, search, neighbors, and shortest path

**Files:**
- Create: `plugins/detective-plugin/tests/test_graph.py`
- Create: `plugins/detective-plugin/detective_mcp/graph.py`

- [ ] **Step 1: Write failing graph tests**

Create `plugins/detective-plugin/tests/test_graph.py`:

```python
from detective_mcp import graph, store


def build_case(tmp_path):
    store.open_case(tmp_path, "Graph Case", "Description", case_id="graph-case")
    observation = store.add_node(tmp_path, "graph-case", "observation", "Config changed on Monday", source="user", tags=["config"])
    evidence = store.add_node(tmp_path, "graph-case", "evidence", "Diff shows timeout changed", source="file", tags=["config", "timeout"])
    hypothesis = store.add_node(tmp_path, "graph-case", "hypothesis", "Timeout change caused regression", source="agent")
    question = store.add_node(tmp_path, "graph-case", "question", "Was traffic higher that day?", source="agent")
    store.add_edge(tmp_path, "graph-case", observation["id"], evidence["id"], "derives")
    store.add_edge(tmp_path, "graph-case", evidence["id"], hypothesis["id"], "supports")
    store.add_edge(tmp_path, "graph-case", question["id"], hypothesis["id"], "requires")
    return observation, evidence, hypothesis, question


def test_graph_overview_counts_roles_and_density(tmp_path):
    build_case(tmp_path)

    overview = graph.graph_overview(tmp_path, "graph-case")

    assert overview["case_id"] == "graph-case"
    assert overview["total_nodes"] == 4
    assert overview["total_edges"] == 3
    assert overview["by_type"]["hypothesis"] == 1
    assert overview["active_hypotheses"] == 1
    assert overview["open_questions"] == 1
    assert overview["graph_density"] == 0.75


def test_list_nodes_filters_by_type_status_and_tag(tmp_path):
    build_case(tmp_path)

    assert len(graph.list_nodes(tmp_path, "graph-case", node_type="evidence")) == 1
    assert len(graph.list_nodes(tmp_path, "graph-case", status="open")) == 4
    assert len(graph.list_nodes(tmp_path, "graph-case", tag="timeout")) == 1


def test_search_nodes_matches_content_and_tags(tmp_path):
    build_case(tmp_path)

    content_matches = graph.search_nodes(tmp_path, "graph-case", query="timeout")
    tag_matches = graph.search_nodes(tmp_path, "graph-case", query="config")

    assert {node["type"] for node in content_matches} >= {"evidence", "hypothesis"}
    assert {node["type"] for node in tag_matches} >= {"observation", "evidence"}


def test_neighbors_returns_incoming_and_outgoing(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    neighbors = graph.neighbors(tmp_path, "graph-case", hypothesis["id"])

    assert {edge["from_id"] for edge in neighbors["incoming_edges"]} == {evidence["id"], question["id"]}
    assert neighbors["outgoing_edges"] == []


def test_shortest_path_directed_and_undirected(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    directed = graph.shortest_path(tmp_path, "graph-case", observation["id"], hypothesis["id"])
    reverse_directed = graph.shortest_path(tmp_path, "graph-case", hypothesis["id"], observation["id"])
    reverse_undirected = graph.shortest_path(tmp_path, "graph-case", hypothesis["id"], observation["id"], undirected=True)

    assert [node["id"] for node in directed["nodes"]] == [observation["id"], evidence["id"], hypothesis["id"]]
    assert reverse_directed["nodes"] == []
    assert [node["id"] for node in reverse_undirected["nodes"]] == [hypothesis["id"], evidence["id"], observation["id"]]
```

- [ ] **Step 2: Run graph tests to verify failure**

Run:

```bash
uv run pytest tests/test_graph.py -v
```

Expected: FAIL because `graph.py` does not exist.

- [ ] **Step 3: Implement graph queries**

Create `plugins/detective-plugin/detective_mcp/graph.py`:

```python
from collections import deque
from pathlib import Path
from typing import Any

from . import store


def _case(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    return store.load_case(workspace, case_id)


def graph_overview(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    nodes = case["nodes"]
    edges = case["edges"]
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for node in nodes:
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1
        by_status[node["status"]] = by_status.get(node["status"], 0) + 1
    active_hypotheses = [node for node in nodes if node["type"] == "hypothesis" and node["status"] not in {"rejected", "stale", "resolved"}]
    open_questions = [node for node in nodes if node["type"] == "question" and node["status"] == "open"]
    density = round(len(edges) / max(len(nodes), 1), 3)
    return {
        "case_id": case_id,
        "title": case["title"],
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "by_type": by_type,
        "by_status": by_status,
        "active_hypotheses": len(active_hypotheses),
        "evidence_count": by_type.get("evidence", 0),
        "constraint_count": by_type.get("constraint", 0),
        "open_questions": len(open_questions),
        "graph_density": density,
    }


def list_nodes(
    workspace: str | Path | None,
    case_id: str,
    node_type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    nodes = list(_case(workspace, case_id)["nodes"])
    if node_type:
        nodes = [node for node in nodes if node["type"] == node_type]
    if status:
        nodes = [node for node in nodes if node["status"] == status]
    if tag:
        nodes = [node for node in nodes if tag in node.get("tags", [])]
    if limit is not None:
        nodes = nodes[:limit]
    return nodes


def get_node(workspace: str | Path | None, case_id: str, node_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    return store.find_node(case, node_id)


def search_nodes(
    workspace: str | Path | None,
    case_id: str,
    query: str,
    types: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    lowered = query.lower()
    matches = []
    for node in _case(workspace, case_id)["nodes"]:
        if types and node["type"] not in types:
            continue
        content_match = lowered in node["content"].lower()
        tag_match = any(lowered in tag.lower() for tag in node.get("tags", []))
        if content_match or tag_match:
            matches.append(node)
    if limit is not None:
        matches = matches[:limit]
    return matches


def list_edges(
    workspace: str | Path | None,
    case_id: str,
    edge_type: str | None = None,
    from_id: str | None = None,
    to_id: str | None = None,
) -> list[dict[str, Any]]:
    edges = list(_case(workspace, case_id)["edges"])
    if edge_type:
        edges = [edge for edge in edges if edge["type"] == edge_type]
    if from_id:
        edges = [edge for edge in edges if edge["from_id"] == from_id]
    if to_id:
        edges = [edge for edge in edges if edge["to_id"] == to_id]
    return edges


def neighbors(workspace: str | Path | None, case_id: str, node_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    store.find_node(case, node_id)
    incoming = [edge for edge in case["edges"] if edge["to_id"] == node_id]
    outgoing = [edge for edge in case["edges"] if edge["from_id"] == node_id]
    node_by_id = {node["id"]: node for node in case["nodes"]}
    neighbor_ids = {edge["from_id"] for edge in incoming} | {edge["to_id"] for edge in outgoing}
    return {
        "node_id": node_id,
        "incoming_edges": incoming,
        "outgoing_edges": outgoing,
        "neighbor_nodes": [node_by_id[item] for item in neighbor_ids if item in node_by_id],
    }


def shortest_path(
    workspace: str | Path | None,
    case_id: str,
    from_id: str,
    to_id: str,
    undirected: bool = False,
) -> dict[str, Any]:
    case = _case(workspace, case_id)
    node_by_id = {node["id"]: node for node in case["nodes"]}
    if from_id not in node_by_id or to_id not in node_by_id:
        return {"nodes": [], "edges": []}

    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {node_id: [] for node_id in node_by_id}
    for edge in case["edges"]:
        adjacency.setdefault(edge["from_id"], []).append((edge["to_id"], edge))
        if undirected:
            adjacency.setdefault(edge["to_id"], []).append((edge["from_id"], edge))

    queue = deque([(from_id, [from_id], [])])
    seen = {from_id}
    while queue:
        current, path_nodes, path_edges = queue.popleft()
        if current == to_id:
            return {
                "nodes": [node_by_id[node_id] for node_id in path_nodes],
                "edges": path_edges,
            }
        for next_id, edge in adjacency.get(current, []):
            if next_id in seen:
                continue
            seen.add(next_id)
            queue.append((next_id, path_nodes + [next_id], path_edges + [edge]))
    return {"nodes": [], "edges": []}
```

- [ ] **Step 4: Run graph tests**

Run:

```bash
uv run pytest tests/test_graph.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/graph.py plugins/detective-plugin/tests/test_graph.py
git commit -m "feat: add detective graph queries"
```

## Task 5: Implement Markdown and Mermaid exports

**Files:**
- Create: `plugins/detective-plugin/tests/test_exports.py`
- Create: `plugins/detective-plugin/detective_mcp/exports.py`

- [ ] **Step 1: Write failing export tests**

Create `plugins/detective-plugin/tests/test_exports.py`:

```python
from pathlib import Path

from detective_mcp import exports, store


def build_export_case(tmp_path):
    store.open_case(tmp_path, "Export Case", "Readable artifacts", case_id="export-case")
    observation = store.add_node(tmp_path, "export-case", "observation", "Initial symptom", source="user")
    evidence = store.add_node(tmp_path, "export-case", "evidence", "Verified log line", source="file")
    hypothesis = store.add_node(tmp_path, "export-case", "hypothesis", "Log line explains symptom", source="agent", confidence=0.8)
    store.add_edge(tmp_path, "export-case", observation["id"], evidence["id"], "derives")
    store.add_edge(tmp_path, "export-case", evidence["id"], hypothesis["id"], "supports", rationale="Log line matches symptom")
    return observation, evidence, hypothesis


def test_export_markdown_writes_notes_file(tmp_path):
    build_export_case(tmp_path)

    result = exports.export_markdown(tmp_path, "export-case")

    path = Path(result["path"])
    assert path.name == "notes.md"
    text = path.read_text()
    assert "# Case: Export Case" in text
    assert "## Active Hypotheses" in text
    assert "Log line explains symptom" in text
    assert "## Evidence" in text
    assert "Verified log line" in text
    assert "## Key Relationships" in text
    assert "supports" in text


def test_export_mermaid_writes_graph_file(tmp_path):
    build_export_case(tmp_path)

    result = exports.export_mermaid(tmp_path, "export-case")

    path = Path(result["path"])
    assert path.name == "graph.mmd"
    text = path.read_text()
    assert text.startswith("graph LR")
    assert "Initial symptom" in text
    assert "-- supports -->" in text
```

- [ ] **Step 2: Run export tests to verify failure**

Run:

```bash
uv run pytest tests/test_exports.py -v
```

Expected: FAIL because `exports.py` does not exist.

- [ ] **Step 3: Implement exports**

Create `plugins/detective-plugin/detective_mcp/exports.py`:

```python
from pathlib import Path
from typing import Any

from . import graph, store


def _truncate(value: str, limit: int = 48) -> str:
    compact = value.replace("\n", " ").strip()
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _escape_mermaid(value: str) -> str:
    return value.replace('"', "'").replace("[", "(").replace("]", ")")


def _case_dir(workspace: str | Path | None, case_id: str) -> Path:
    return store.case_dir(workspace, case_id)


def export_markdown(workspace: str | Path | None, case_id: str) -> dict[str, str]:
    case = store.load_case(workspace, case_id)
    overview = graph.graph_overview(workspace, case_id)
    nodes = case["nodes"]
    edges = case["edges"]

    def nodes_of(node_type: str) -> list[dict[str, Any]]:
        return [node for node in nodes if node["type"] == node_type]

    lines = [
        f"# Case: {case['title']}",
        "",
        case["description"],
        "",
        "## Overview",
        "",
        f"- Case ID: `{case_id}`",
        f"- Nodes: {overview['total_nodes']}",
        f"- Edges: {overview['total_edges']}",
        f"- Active hypotheses: {overview['active_hypotheses']}",
        f"- Evidence count: {overview['evidence_count']}",
        f"- Open questions: {overview['open_questions']}",
        "",
        "## Active Hypotheses",
        "",
    ]

    hypotheses = [node for node in nodes_of("hypothesis") if node["status"] not in {"rejected", "stale", "resolved"}]
    if hypotheses:
        for node in hypotheses:
            lines.append(f"- `{node['id']}` ({node['confidence']:.2f}) {node['content']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Evidence", ""])
    evidence = nodes_of("evidence")
    if evidence:
        for node in evidence:
            lines.append(f"- `{node['id']}` {node['content']} (source: {node['source']})")
    else:
        lines.append("- None")

    lines.extend(["", "## Constraints", ""])
    constraints = nodes_of("constraint")
    if constraints:
        for node in constraints:
            lines.append(f"- `{node['id']}` {node['content']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Open Questions", ""])
    questions = [node for node in nodes_of("question") if node["status"] == "open"]
    if questions:
        for node in questions:
            lines.append(f"- `{node['id']}` {node['content']}")
    else:
        lines.append("- None")

    lines.extend(["", "## Key Relationships", ""])
    if edges:
        for edge in edges:
            lines.append(f"- `{edge['from_id']}` --{edge['type']}--> `{edge['to_id']}` {edge.get('rationale', '')}".rstrip())
    else:
        lines.append("- None")

    lines.extend(["", "## Recent Actions", ""])
    actions = case.get("actions", [])[-5:]
    if actions:
        for action in actions:
            lines.append(f"- {action}")
    else:
        lines.append("- None")

    output = _case_dir(workspace, case_id) / "notes.md"
    output.write_text("\n".join(lines) + "\n")
    return {"case_id": case_id, "path": str(output)}


def export_mermaid(workspace: str | Path | None, case_id: str) -> dict[str, str]:
    case = store.load_case(workspace, case_id)
    lines = ["graph LR"]
    for node in case["nodes"]:
        label = _escape_mermaid(f"{node['type']}: {_truncate(node['content'])}")
        lines.append(f"  {node['id']}[\"{label}\"]")
    for edge in case["edges"]:
        lines.append(f"  {edge['from_id']} -- {edge['type']} --> {edge['to_id']}")
    output = _case_dir(workspace, case_id) / "graph.mmd"
    output.write_text("\n".join(lines) + "\n")
    return {"case_id": case_id, "path": str(output)}
```

- [ ] **Step 4: Run export tests**

Run:

```bash
uv run pytest tests/test_exports.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/exports.py plugins/detective-plugin/tests/test_exports.py
git commit -m "feat: export detective graph artifacts"
```

## Task 6: Expose MCP server tools

**Files:**
- Create: `plugins/detective-plugin/tests/test_server_tools.py`
- Create: `plugins/detective-plugin/detective_mcp/server.py`

- [ ] **Step 1: Write failing server tool tests**

Create `plugins/detective-plugin/tests/test_server_tools.py`:

```python
from pathlib import Path

from detective_mcp import server


def test_server_tool_wrappers_create_and_query_case(tmp_path):
    opened = server.detective_open_case(
        title="Server Case",
        description="Tool wrapper smoke test",
        case_id="server-case",
        workspace=str(tmp_path),
    )
    observation = server.detective_add_node(
        case_id="server-case",
        type="observation",
        content="Observed behavior",
        source="user",
        workspace=str(tmp_path),
    )
    hypothesis = server.detective_add_node(
        case_id="server-case",
        type="hypothesis",
        content="Possible explanation",
        source="agent",
        workspace=str(tmp_path),
    )
    edge = server.detective_add_edge(
        case_id="server-case",
        from_id=observation["id"],
        to_id=hypothesis["id"],
        type="supports",
        workspace=str(tmp_path),
    )

    overview = server.detective_graph_overview("server-case", workspace=str(tmp_path))
    path = server.detective_shortest_path("server-case", observation["id"], hypothesis["id"], workspace=str(tmp_path))

    assert opened["case_id"] == "server-case"
    assert edge["type"] == "supports"
    assert overview["total_nodes"] == 2
    assert [node["id"] for node in path["nodes"]] == [observation["id"], hypothesis["id"]]


def test_server_tool_wrappers_export_files(tmp_path):
    server.detective_open_case("Export Server", "Description", case_id="export-server", workspace=str(tmp_path))
    server.detective_add_node("export-server", "evidence", "Evidence text", workspace=str(tmp_path))

    markdown = server.detective_export_markdown("export-server", workspace=str(tmp_path))
    mermaid = server.detective_export_mermaid("export-server", workspace=str(tmp_path))

    assert Path(markdown["path"]).exists()
    assert Path(mermaid["path"]).exists()
```

- [ ] **Step 2: Run server tests to verify failure**

Run:

```bash
uv run pytest tests/test_server_tools.py -v
```

Expected: FAIL because `server.py` is missing.

- [ ] **Step 3: Implement FastMCP server**

Create `plugins/detective-plugin/detective_mcp/server.py`:

```python
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import exports, graph, store

mcp = FastMCP("detective")


@mcp.tool()
def detective_open_case(
    title: str,
    description: str,
    case_id: str | None = None,
    config: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> dict[str, str]:
    return store.open_case(workspace, title, description, case_id, config)


@mcp.tool()
def detective_load_case(case_id: str, workspace: str | None = None) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    return {
        "case_id": case["id"],
        "title": case["title"],
        "description": case["description"],
        "nodes": len(case["nodes"]),
        "edges": len(case["edges"]),
        "updated_at": case["updated_at"],
    }


@mcp.tool()
def detective_save_case(case_id: str, workspace: str | None = None) -> dict[str, str]:
    case = store.load_case(workspace, case_id)
    return store.save_case(workspace, case, event={"type": "case_saved", "case_id": case_id})


@mcp.tool()
def detective_graph_overview(case_id: str, workspace: str | None = None) -> dict[str, Any]:
    return graph.graph_overview(workspace, case_id)


@mcp.tool()
def detective_add_node(
    case_id: str,
    type: str,
    content: str,
    status: str = "open",
    confidence: float = 0.5,
    source: str = "system",
    tags: list[str] | None = None,
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    return store.add_node(workspace, case_id, type, content, status, confidence, source, tags, created_by, metadata)


@mcp.tool()
def detective_update_node(
    case_id: str,
    node_id: str,
    content: str | None = None,
    status: str | None = None,
    confidence: float | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    return store.update_node(workspace, case_id, node_id, content, status, confidence, tags, metadata)


@mcp.tool()
def detective_get_node(case_id: str, node_id: str, workspace: str | None = None) -> dict[str, Any]:
    return graph.get_node(workspace, case_id, node_id)


@mcp.tool()
def detective_list_nodes(
    case_id: str,
    type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    return graph.list_nodes(workspace, case_id, type, status, tag, limit)


@mcp.tool()
def detective_search_nodes(
    case_id: str,
    query: str,
    types: list[str] | None = None,
    limit: int | None = None,
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    return graph.search_nodes(workspace, case_id, query, types, limit)


@mcp.tool()
def detective_add_edge(
    case_id: str,
    from_id: str,
    to_id: str,
    type: str,
    confidence: float = 0.5,
    rationale: str = "",
    created_by: str = "system",
    metadata: dict[str, Any] | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    return store.add_edge(workspace, case_id, from_id, to_id, type, confidence, rationale, created_by, metadata)


@mcp.tool()
def detective_list_edges(
    case_id: str,
    type: str | None = None,
    from_id: str | None = None,
    to_id: str | None = None,
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    return graph.list_edges(workspace, case_id, type, from_id, to_id)


@mcp.tool()
def detective_neighbors(case_id: str, node_id: str, workspace: str | None = None) -> dict[str, Any]:
    return graph.neighbors(workspace, case_id, node_id)


@mcp.tool()
def detective_shortest_path(
    case_id: str,
    from_id: str,
    to_id: str,
    undirected: bool = False,
    workspace: str | None = None,
) -> dict[str, Any]:
    return graph.shortest_path(workspace, case_id, from_id, to_id, undirected)


@mcp.tool()
def detective_export_markdown(case_id: str, workspace: str | None = None) -> dict[str, str]:
    return exports.export_markdown(workspace, case_id)


@mcp.tool()
def detective_export_mermaid(case_id: str, workspace: str | None = None) -> dict[str, str]:
    return exports.export_mermaid(workspace, case_id)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run server tests**

Run:

```bash
uv run pytest tests/test_server_tools.py -v
```

Expected: PASS.

- [ ] **Step 5: Run the full plugin test suite**

Run:

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Start server import smoke test**

Run:

```bash
uv run python -c "from detective_mcp.server import mcp; print(mcp.name)"
```

Expected output contains:

```text
detective
```

- [ ] **Step 7: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/server.py plugins/detective-plugin/tests/test_server_tools.py
git commit -m "feat: expose detective MCP tools"
```

## Task 7: Refactor legacy scripts into utility-backed CLI wrappers

**Files:**
- Create: `plugins/detective-plugin/tests/test_legacy_scripts.py`
- Create: `plugins/detective-plugin/detective_mcp/legacy_board.py`
- Create: `plugins/detective-plugin/detective_mcp/legacy_scoring.py`
- Create: `plugins/detective-plugin/detective_mcp/legacy_convergence.py`
- Modify: `plugins/detective-plugin/scripts/board.py`
- Modify: `plugins/detective-plugin/scripts/scoring.py`
- Modify: `plugins/detective-plugin/scripts/convergence.py`

- [ ] **Step 1: Write failing legacy script tests**

Create `plugins/detective-plugin/tests/test_legacy_scripts.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name, *args):
    return subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / script_name), *args],
        cwd=PLUGIN_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )


def test_board_script_delegates_to_legacy_board_utils(tmp_path):
    case_file = tmp_path / "case.json"

    created = run_script("board.py", "init", str(case_file), "Legacy Case", "Description")
    assert json.loads(created.stdout)["status"] == "created"

    fragment = json.dumps({"content": "Config drift", "role": "hypothesis", "maturity": "clue"})
    added = run_script("board.py", "add-fragment", str(case_file), fragment)
    fragment_id = json.loads(added.stdout)["id"]

    status = json.loads(run_script("board.py", "status", str(case_file)).stdout)
    assert status["title"] == "Legacy Case"
    assert status["active_hypotheses"] == 1

    evolved = json.loads(run_script("board.py", "evolve", str(case_file), fragment_id, "evidence").stdout)
    assert evolved == {"evolved": True}

    graph = run_script("board.py", "export-graph", str(case_file)).stdout
    assert graph.startswith("digraph CaseBoard")
    assert fragment_id in graph


def test_scoring_script_delegates_to_legacy_scoring_utils(tmp_path):
    case_file = tmp_path / "score.json"
    board = {
        "id": "legacy-score",
        "title": "Score",
        "phase": "opening",
        "fragments": [
            {"id": "h1", "role": "hypothesis", "maturity": "clue", "confidence": 0.5},
            {"id": "c1", "role": "constraint", "maturity": "evidence", "confidence": 1.0},
        ],
        "threads": [{"from_id": "c1", "to_id": "h1", "type": "contradicts"}],
        "actions_history": [],
        "config": {"confidence_threshold_eliminate": 0.15},
    }
    case_file.write_text(json.dumps(board), encoding="utf-8")

    phase = json.loads(run_script("scoring.py", "suggest-phase", str(case_file)).stdout)
    assert phase["suggested_phase"] in {"opening", "pursuit"}

    candidates = json.dumps([
        {"description": "Check h1", "target_hypotheses": ["h1"], "feasibility": 0.8, "cost": 2}
    ])
    scored = json.loads(run_script("scoring.py", "score-actions", str(case_file), candidates).stdout)
    assert scored[0]["description"] == "Check h1"
    assert scored[0]["score"] > 0

    changes = json.loads(run_script("scoring.py", "propagate", str(case_file)).stdout)
    assert changes["weakened"] == [{"id": "h1", "new_confidence": 0.35}]


def test_convergence_script_delegates_to_legacy_convergence_utils(tmp_path):
    case_file = tmp_path / "converged.json"
    board = {
        "id": "legacy-converged",
        "title": "Converged",
        "fragments": [
            {"id": "h1", "role": "hypothesis", "maturity": "evidence", "confidence": 0.9},
            {"id": "h2", "role": "hypothesis", "maturity": "clue", "confidence": 0.1, "status": "eliminated"},
        ],
        "threads": [],
        "config": {"confidence_threshold_confirm": 0.85, "confidence_threshold_eliminate": 0.15},
    }
    case_file.write_text(json.dumps(board), encoding="utf-8")

    result = json.loads(run_script("convergence.py", str(case_file)).stdout)
    assert result["converged"] is True
    assert result["recommendation"] == "close-case"
```

- [ ] **Step 2: Run tests to verify failure**

Run from `plugins/detective-plugin`:

```bash
uv run pytest tests/test_legacy_scripts.py -v
```

Expected: FAIL because `detective_mcp.legacy_board`, `detective_mcp.legacy_scoring`, and `detective_mcp.legacy_convergence` do not exist yet after wrappers are introduced, or because wrappers still contain duplicated logic before refactor.

- [ ] **Step 3: Move board logic into `legacy_board.py`**

Create `plugins/detective-plugin/detective_mcp/legacy_board.py` by moving the existing pure functions from `scripts/board.py` into the package module:

- `_new_id`
- `_now`
- `init_case`
- `add_fragment`
- `add_thread`
- `evolve_fragment`
- `eliminate_fragment`
- `get_active_hypotheses`
- `get_fragments_by_role`
- `get_threads_for`
- `board_summary`
- `export_dot`
- `load_board`
- `save_board`

Use UTF-8 for `load_board` and `save_board`:

```python
return json.loads(Path(path).read_text(encoding="utf-8"))
Path(path).write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Replace `scripts/board.py` with a thin wrapper**

Replace `plugins/detective-plugin/scripts/board.py` with a CLI wrapper that imports `detective_mcp.legacy_board` and contains no graph/business logic beyond argument parsing and printing JSON.

The wrapper must prepend the plugin root to `sys.path` so direct script execution works:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from detective_mcp import legacy_board


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__ or "Usage: python board.py <command> <case_file> [args...]")
        return 1
    cmd = argv[1]
    case_file = argv[2]
    if cmd == "init":
        title = argv[3] if len(argv) > 3 else "Untitled Case"
        desc = argv[4] if len(argv) > 4 else ""
        board = legacy_board.init_case(title, desc)
        legacy_board.save_board(board, case_file)
        print(json.dumps({"status": "created", "case_id": board["id"]}, indent=2))
        return 0
    board = legacy_board.load_board(case_file)
    if cmd == "add-fragment":
        result = legacy_board.add_fragment(board, json.loads(argv[3]))
        legacy_board.save_board(board, case_file)
        print(json.dumps(result, indent=2))
        return 0
    if cmd == "add-thread":
        result = legacy_board.add_thread(board, json.loads(argv[3]))
        legacy_board.save_board(board, case_file)
        print(json.dumps(result, indent=2))
        return 0
    if cmd == "evolve":
        ok = legacy_board.evolve_fragment(board, argv[3], argv[4])
        legacy_board.save_board(board, case_file)
        print(json.dumps({"evolved": ok}))
        return 0
    if cmd == "eliminate":
        reason = argv[4] if len(argv) > 4 else "no reason given"
        ok = legacy_board.eliminate_fragment(board, argv[3], reason)
        legacy_board.save_board(board, case_file)
        print(json.dumps({"eliminated": ok}))
        return 0
    if cmd == "status":
        print(json.dumps(legacy_board.board_summary(board), indent=2))
        return 0
    if cmd == "export-graph":
        print(legacy_board.export_dot(board))
        return 0
    print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 5: Move scoring logic into `legacy_scoring.py` and wrap script**

Create `plugins/detective-plugin/detective_mcp/legacy_scoring.py` by moving the existing pure functions from `scripts/scoring.py`:

- `load_board`
- `save_board`
- `propagate_constraints`
- `score_candidate_actions`
- `suggest_phase`

Use UTF-8 for file I/O.

Replace `plugins/detective-plugin/scripts/scoring.py` with a wrapper that imports `detective_mcp.legacy_scoring`, parses `propagate`, `score-actions`, and `suggest-phase`, and prints JSON results. It must contain no propagation/scoring/phase business logic.

- [ ] **Step 6: Move convergence logic into `legacy_convergence.py` and wrap script**

Create `plugins/detective-plugin/detective_mcp/legacy_convergence.py` by moving the existing pure functions from `scripts/convergence.py`:

- `load_board`
- `check_convergence`

Use UTF-8 for file I/O.

Replace `plugins/detective-plugin/scripts/convergence.py` with a wrapper that imports `detective_mcp.legacy_convergence`, loads the board, calls `check_convergence`, and prints JSON. It must contain no convergence business logic.

- [ ] **Step 7: Run legacy script tests**

Run:

```bash
uv run pytest tests/test_legacy_scripts.py -v
```

Expected: PASS.

- [ ] **Step 8: Run v2 regression tests**

Run:

```bash
uv run pytest tests/test_config.py tests/test_store.py tests/test_graph.py tests/test_legacy_scripts.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/legacy_board.py plugins/detective-plugin/detective_mcp/legacy_scoring.py plugins/detective-plugin/detective_mcp/legacy_convergence.py plugins/detective-plugin/scripts/board.py plugins/detective-plugin/scripts/scoring.py plugins/detective-plugin/scripts/convergence.py plugins/detective-plugin/tests/test_legacy_scripts.py
git commit -m "refactor: reuse detective utilities in legacy scripts"
```

## Task 8: Document v2 MCP usage and bump plugin metadata

**Files:**
- Modify: `plugins/detective-plugin/README.md`
- Modify: `plugins/detective-plugin/README-zh.md`
- Modify: `plugins/detective-plugin/.claude-plugin/plugin.json`

- [ ] **Step 1: Update plugin metadata**

Modify `plugins/detective-plugin/.claude-plugin/plugin.json` to:

```json
{
  "name": "detective",
  "version": "0.2.0",
  "description": "A general-purpose AI investigation framework with a local MCP graph core. Maintains project-local CaseBoard state under .detective/ and supports evidence chains, graph search, shortest paths, Markdown/Mermaid exports, parallel hypotheses, constraint propagation, and autonomous convergence workflows.",
  "author": {
    "name": "Esonhugh",
    "url": "https://github.com/esonhugh"
  },
  "keywords": ["investigation", "reasoning", "problem-solving", "agent", "detective", "hypothesis", "mcp", "graph"]
}
```

- [ ] **Step 2: Add English README v2 section**

Insert after the existing Usage section in `plugins/detective-plugin/README.md`:

```markdown
## v2 MCP Graph Core

Detective v2 includes a local stdio MCP server registered by `.mcp.json` and launched with `uv`. The MCP server is the preferred state interface for new workflows.

Core tools:

- `detective_open_case`
- `detective_load_case`
- `detective_save_case`
- `detective_graph_overview`
- `detective_add_node`
- `detective_update_node`
- `detective_get_node`
- `detective_list_nodes`
- `detective_search_nodes`
- `detective_add_edge`
- `detective_list_edges`
- `detective_neighbors`
- `detective_shortest_path`
- `detective_export_markdown`
- `detective_export_mermaid`

Canonical state is stored in the current project:

```text
.detective/cases/<case-id>/case.json
```

Generated review artifacts are stored next to it:

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

JSON is the only canonical state source. Markdown and Mermaid are generated projections.
```

- [ ] **Step 3: Add Chinese README v2 section**

Insert after the existing Usage section in `plugins/detective-plugin/README-zh.md`:

```markdown
## v2 MCP 图核心

Detective v2 提供一个通过 `.mcp.json` 注册、由 `uv` 启动的本地 stdio MCP 服务。新的工作流应优先通过 MCP 工具读写调查图状态。

核心工具：

- `detective_open_case`
- `detective_load_case`
- `detective_save_case`
- `detective_graph_overview`
- `detective_add_node`
- `detective_update_node`
- `detective_get_node`
- `detective_list_nodes`
- `detective_search_nodes`
- `detective_add_edge`
- `detective_list_edges`
- `detective_neighbors`
- `detective_shortest_path`
- `detective_export_markdown`
- `detective_export_mermaid`

权威状态存储在当前项目：

```text
.detective/cases/<case-id>/case.json
```

生成的人类可读产物保存在同一目录：

```text
.detective/cases/<case-id>/notes.md
.detective/cases/<case-id>/graph.mmd
.detective/cases/<case-id>/events.jsonl
```

JSON 是唯一权威状态源。Markdown 和 Mermaid 都是从 JSON 生成的视图。
```

- [ ] **Step 4: Run documentation sanity checks**

Run:

```bash
grep -R "detective_open_case\|detective_shortest_path\|v2 MCP" -n README.md README-zh.md .claude-plugin/plugin.json
```

Expected: output includes matches in both README files and plugin JSON.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/README.md plugins/detective-plugin/README-zh.md plugins/detective-plugin/.claude-plugin/plugin.json
git commit -m "docs: document detective MCP graph core"
```

## Task 9: Final validation for v2

**Files:**
- Verify all v2 files.

- [ ] **Step 1: Run full tests**

Run from `plugins/detective-plugin`:

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run import and module smoke checks**

Run:

```bash
uv run python -m detective_mcp.server --help
```

Expected: the process may wait for MCP stdio input or print SDK help depending on MCP SDK behavior. Stop it with Ctrl-C if it waits; there must be no immediate import traceback.

- [ ] **Step 3: Validate MCP registration JSON**

Run:

```bash
python -m json.tool .mcp.json >/tmp/detective-mcp-json-check.json
```

Expected: command exits 0.

- [ ] **Step 4: Check git diff**

Run from repository root:

```bash
git diff -- plugins/detective-plugin docs/superpowers/specs docs/superpowers/plans
```

Expected: diff contains only intended Detective v2 MCP files, tests, docs, specs, and plans.

- [ ] **Step 5: Manual Claude Code MCP check**

Restart Claude Code or reload plugins, then run `/mcp` and verify a plugin-provided `detective` server appears. Expected MCP tools include `detective_open_case`, `detective_add_node`, `detective_graph_overview`, and `detective_shortest_path`.

- [ ] **Step 6: Final commit if commits are authorized**

```bash
git add plugins/detective-plugin docs/superpowers/specs docs/superpowers/plans
git commit -m "feat: add detective MCP graph core"
```
