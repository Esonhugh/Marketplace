import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from detective_mcp import actions, blackboard, coverage, ooda, proof, server, store


def test_legacy_schema_is_rejected_without_migration(tmp_path):
    case_dir = tmp_path / ".detective" / "cases" / "legacy"
    case_dir.mkdir(parents=True)
    (case_dir / "case.json").write_text(json.dumps({
        "schema_version": "2.0",
        "id": "legacy",
        "title": "Legacy",
        "description": "Old case",
        "nodes": [],
        "edges": [],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported Detective case schema"):
        store.load_case(tmp_path, "legacy")


def test_concurrent_writes_are_serialized_and_revisioned(tmp_path):
    store.open_case(tmp_path, "Concurrent", "Description", case_id="concurrent")

    def add(index: int):
        return store.add_node(tmp_path, "concurrent", "observation", f"node {index}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = [node["id"] for node in pool.map(add, range(20))]

    case = store.load_case(tmp_path, "concurrent")
    assert len(case["nodes"]) == 20
    assert len(set(ids)) == 20
    assert case["revision"] == 21


def test_expected_revision_conflict(tmp_path):
    store.open_case(tmp_path, "Revision", "Description", case_id="revision")
    case = store.load_case(tmp_path, "revision")
    store.add_node(tmp_path, "revision", "observation", "new")

    with pytest.raises(store.RevisionConflictError):
        store.save_case(tmp_path, case, expected_revision=case["revision"])


def test_ooda_blackboard_actions_coverage_and_proof_flow(tmp_path):
    store.open_case(tmp_path, "Flow", "Description", case_id="flow")
    phase = ooda.transition_phase(tmp_path, "flow", "orient", "sort evidence")
    intent = ooda.add_intent(tmp_path, "flow", "identify root cause")
    entry = blackboard.add_entry(tmp_path, "flow", "maybe cache", tags=["cache"])
    promoted = blackboard.promote_entry(tmp_path, "flow", entry["id"], "hypothesis", confidence=0.9)
    store.update_node(tmp_path, "flow", promoted["node"]["id"], status="confirmed")
    evidence = store.add_node(tmp_path, "flow", "evidence", "trace proves cache", status="confirmed", confidence=1.0, source="file")
    store.add_edge(tmp_path, "flow", evidence["id"], promoted["node"]["id"], "supports")
    action = actions.add_action(tmp_path, "flow", "inspect trace", priority=0.8)
    actions.update_action(tmp_path, "flow", action["id"], status="done")
    actions.add_checkpoint(tmp_path, "flow", "trace inspected", action_id=action["id"])
    cov = coverage.add_item(tmp_path, "flow", "logs", status="complete")
    evaluated = proof.evaluate(tmp_path, "flow", "cache proof")
    gate = proof.completion_gate(tmp_path, "flow")
    closed = proof.close_case(tmp_path, "flow", "cache caused it")

    assert phase["phase"] == "orient"
    assert intent["intent"] == "identify root cause"
    assert promoted["entry"]["status"] == "promoted"
    assert cov["status"] == "complete"
    assert evaluated["status"] == "passes"
    assert gate["allowed"] is True
    assert closed["status"] == "closed"


@pytest.mark.anyio
async def test_server_registers_v04_tools():
    tool_names = {tool.name for tool in await server.mcp.list_tools()}
    for name in {
        "detective_case_status",
        "detective_transition_phase",
        "detective_blackboard_promote",
        "detective_coverage_status",
        "detective_evaluate_proof",
        "detective_completion_gate",
        "detective_close_case",
        "detective_list_events",
    }:
        assert name in tool_names
