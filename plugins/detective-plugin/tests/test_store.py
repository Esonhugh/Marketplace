import json

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

    data = json.loads(case_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "4.0"
    assert data["status"] == "open"
    assert data["revision"] == 1
    assert data["id"] == "strange-behavior"
    assert data["title"] == "Investigate strange behavior"
    assert data["config"]["autonomy"] == "full_auto"
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["actions"] == []
    assert "scheduler" not in data


def test_open_case_generates_slug_when_case_id_missing(tmp_path):
    result = store.open_case(
        workspace=tmp_path,
        title="Config Drift? Maybe!",
        description="Check generated IDs",
    )

    assert result["case_id"] == "config-drift-maybe"
    assert (tmp_path / ".detective" / "cases" / "config-drift-maybe" / "case.json").exists()


def test_open_case_uses_detective_workspace_env_when_workspace_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DETECTIVE_WORKSPACE", str(tmp_path))

    result = store.open_case(
        workspace=None,
        title="Environment Case",
        description="Uses DETECTIVE_WORKSPACE",
        case_id="env-case",
    )

    case_path = tmp_path / ".detective" / "cases" / "env-case" / "case.json"
    assert result["case_path"] == str(case_path)
    assert case_path.exists()


def test_load_case_returns_existing_case(tmp_path):
    store.open_case(tmp_path, "A Case", "Description", case_id="a-case")

    loaded = store.load_case(tmp_path, "a-case")

    assert loaded["id"] == "a-case"
    assert loaded["title"] == "A Case"


def test_load_case_raises_for_missing_case(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing-case"):
        store.load_case(tmp_path, "missing-case")


def test_open_case_rejects_existing_case_and_preserves_nodes(tmp_path):
    store.open_case(tmp_path, "Original Case", "Description", case_id="existing-case")
    node = store.add_node(tmp_path, "existing-case", "observation", "Original observation")

    with pytest.raises(FileExistsError, match="existing-case"):
        store.open_case(tmp_path, "Replacement Case", "New description", case_id="existing-case")

    case_path = tmp_path / ".detective" / "cases" / "existing-case" / "case.json"
    data = json.loads(case_path.read_text(encoding="utf-8"))
    assert data["title"] == "Original Case"
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["id"] == node["id"]
    assert data["nodes"][0]["content"] == "Original observation"


@pytest.mark.parametrize("bad_case_id", ["../x", "a/b", r"..\x", r"a\b"])
@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda workspace, case_id: store.case_dir(workspace, case_id), id="case_dir"),
        pytest.param(lambda workspace, case_id: store.case_file(workspace, case_id), id="case_file"),
        pytest.param(lambda workspace, case_id: store.events_file(workspace, case_id), id="events_file"),
        pytest.param(
            lambda workspace, case_id: store.open_case(workspace, "Unsafe Case", "Description", case_id=case_id),
            id="open_case",
        ),
        pytest.param(lambda workspace, case_id: store.load_case(workspace, case_id), id="load_case"),
        pytest.param(
            lambda workspace, case_id: store.save_case(workspace, {"id": case_id}, event={"type": "unsafe"}),
            id="save_case",
        ),
        pytest.param(lambda workspace, case_id: store.append_event(workspace, case_id, {"type": "unsafe"}), id="append_event"),
        pytest.param(lambda workspace, case_id: store.add_node(workspace, case_id, "observation", "Unsafe"), id="add_node"),
        pytest.param(
            lambda workspace, case_id: store.update_node(workspace, case_id, "node-id", status="open"),
            id="update_node",
        ),
        pytest.param(
            lambda workspace, case_id: store.add_edge(workspace, case_id, "from-id", "to-id", "supports"),
            id="add_edge",
        ),
    ],
)
def test_public_store_entry_points_reject_unsafe_case_ids(tmp_path, operation, bad_case_id):
    with pytest.raises(ValueError, match="Invalid case_id"):
        operation(tmp_path, bad_case_id)


def test_mutation_appends_event_log_as_distinct_jsonl_events_in_order(tmp_path):
    store.open_case(tmp_path, "Event Case", "Description", case_id="event-case")
    case = store.load_case(tmp_path, "event-case")
    store.save_case(tmp_path, case, event={"type": "first_event", "message": "first"})
    case = store.load_case(tmp_path, "event-case")
    store.save_case(tmp_path, case, event={"type": "second_event", "message": "second"})

    events = tmp_path / ".detective" / "cases" / "event-case" / "events.jsonl"
    assert events.exists()
    records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    assert [record["type"] for record in records] == ["case_opened", "first_event", "second_event"]
    assert [record.get("message") for record in records[1:]] == ["first", "second"]
    assert all("timestamp" in record for record in records)


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


def test_delete_node_removes_incident_edges_and_persists(tmp_path):
    store.open_case(tmp_path, "Delete Node", "Description", case_id="delete-node")
    observation = store.add_node(tmp_path, "delete-node", "observation", "Fact A")
    evidence = store.add_node(tmp_path, "delete-node", "evidence", "Fact B")
    hypothesis = store.add_node(tmp_path, "delete-node", "hypothesis", "Fact C")
    incoming = store.add_edge(tmp_path, "delete-node", observation["id"], evidence["id"], "derives")
    outgoing = store.add_edge(tmp_path, "delete-node", evidence["id"], hypothesis["id"], "supports")

    deleted = store.delete_node(tmp_path, "delete-node", evidence["id"])

    loaded = store.load_case(tmp_path, "delete-node")
    assert deleted["id"] == evidence["id"]
    assert [node["id"] for node in loaded["nodes"]] == [observation["id"], hypothesis["id"]]
    assert loaded["edges"] == []

    events = tmp_path / ".detective" / "cases" / "delete-node" / "events.jsonl"
    records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["type"] == "node_deleted"
    assert records[-1]["node_id"] == evidence["id"]
    assert records[-1]["removed_edges"] == 2
    assert {incoming["id"], outgoing["id"]}


def test_delete_node_rejects_missing_node(tmp_path):
    store.open_case(tmp_path, "Delete Node", "Description", case_id="delete-missing-node")

    with pytest.raises(KeyError, match="Node not found: missing-node"):
        store.delete_node(tmp_path, "delete-missing-node", "missing-node")


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


def test_update_edge_persists_type_confidence_rationale_metadata(tmp_path):
    store.open_case(tmp_path, "Update Edge", "Description", case_id="update-edge")
    left = store.add_node(tmp_path, "update-edge", "observation", "Left")
    right = store.add_node(tmp_path, "update-edge", "hypothesis", "Right")
    edge = store.add_edge(
        tmp_path,
        "update-edge",
        left["id"],
        right["id"],
        "supports",
        confidence=0.2,
        rationale="Initial rationale",
        metadata={"initial": True},
    )

    updated = store.update_edge(
        tmp_path,
        "update-edge",
        edge["id"],
        edge_type="contradicts",
        confidence=0.8,
        rationale="Updated rationale",
        metadata={"reviewed": True},
    )

    loaded = store.load_case(tmp_path, "update-edge")
    persisted = loaded["edges"][0]
    assert updated["id"] == edge["id"]
    assert persisted["type"] == "contradicts"
    assert persisted["confidence"] == 0.8
    assert persisted["rationale"] == "Updated rationale"
    assert persisted["metadata"] == {"initial": True, "reviewed": True}

    events = tmp_path / ".detective" / "cases" / "update-edge" / "events.jsonl"
    records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["type"] == "edge_updated"
    assert records[-1]["edge_id"] == edge["id"]


def test_update_edge_rejects_invalid_type_and_confidence(tmp_path):
    store.open_case(tmp_path, "Update Edge", "Description", case_id="update-edge-invalid")
    left = store.add_node(tmp_path, "update-edge-invalid", "observation", "Left")
    right = store.add_node(tmp_path, "update-edge-invalid", "hypothesis", "Right")
    edge = store.add_edge(tmp_path, "update-edge-invalid", left["id"], right["id"], "supports")

    with pytest.raises(ValueError, match="Invalid edge type"):
        store.update_edge(tmp_path, "update-edge-invalid", edge["id"], edge_type="blocks")

    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        store.update_edge(tmp_path, "update-edge-invalid", edge["id"], confidence=2)


def test_delete_edge_removes_edge_and_persists(tmp_path):
    store.open_case(tmp_path, "Delete Edge", "Description", case_id="delete-edge")
    left = store.add_node(tmp_path, "delete-edge", "observation", "Left")
    right = store.add_node(tmp_path, "delete-edge", "hypothesis", "Right")
    edge = store.add_edge(tmp_path, "delete-edge", left["id"], right["id"], "supports")

    deleted = store.delete_edge(tmp_path, "delete-edge", edge["id"])

    loaded = store.load_case(tmp_path, "delete-edge")
    assert deleted["id"] == edge["id"]
    assert loaded["edges"] == []

    events = tmp_path / ".detective" / "cases" / "delete-edge" / "events.jsonl"
    records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["type"] == "edge_deleted"
    assert records[-1]["edge_id"] == edge["id"]


def test_delete_edge_rejects_missing_edge(tmp_path):
    store.open_case(tmp_path, "Delete Edge", "Description", case_id="delete-edge-missing")

    with pytest.raises(KeyError, match="Edge not found: missing-edge"):
        store.delete_edge(tmp_path, "delete-edge-missing", "missing-edge")


def test_find_edge_rejects_missing_edge(tmp_path):
    store.open_case(tmp_path, "Find Edge", "Description", case_id="find-edge")
    case = store.load_case(tmp_path, "find-edge")

    with pytest.raises(KeyError, match="Edge not found: missing-edge"):
        store.find_edge(case, "missing-edge")


def test_validation_rejects_invalid_values(tmp_path):
    store.open_case(tmp_path, "Validation", "Description", case_id="validation")

    with pytest.raises(ValueError, match="Invalid node type"):
        store.add_node(tmp_path, "validation", "invalid", "Bad node")

    node_a = store.add_node(tmp_path, "validation", "observation", "A")
    node_b = store.add_node(tmp_path, "validation", "hypothesis", "B")
    with pytest.raises(ValueError, match="Invalid edge type"):
        store.add_edge(tmp_path, "validation", node_a["id"], node_b["id"], "blocks")
