import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from detective_mcp import actions, blackboard, coverage, graph, proof, store


def make_closable_case(tmp_path, case_id="closable"):
    store.open_case(tmp_path, "Closable", "Description", case_id=case_id)
    hypothesis = store.add_node(tmp_path, case_id, "hypothesis", "Root cause", status="confirmed", confidence=0.9)
    evidence = store.add_node(tmp_path, case_id, "evidence", "Direct proof", status="confirmed", confidence=1.0)
    store.add_edge(tmp_path, case_id, evidence["id"], hypothesis["id"], "supports")
    coverage.add_item(tmp_path, case_id, "scope", status="complete")
    return hypothesis, evidence


def test_empty_coverage_does_not_satisfy_completion_gate(tmp_path):
    store.open_case(tmp_path, "No Coverage", "Description", case_id="no-coverage")
    hypothesis = store.add_node(tmp_path, "no-coverage", "hypothesis", "Root cause", status="confirmed", confidence=0.9)
    evidence = store.add_node(tmp_path, "no-coverage", "evidence", "Direct proof", status="confirmed", confidence=1.0)
    store.add_edge(tmp_path, "no-coverage", evidence["id"], hypothesis["id"], "supports")

    gate = proof.completion_gate(tmp_path, "no-coverage")

    assert gate["allowed"] is False
    assert gate["current_proof"]["coverage"]["complete"] is False
    assert "coverage is incomplete" in gate["blockers"]



def test_concurrent_same_id_open_is_atomic_create_if_absent(tmp_path):
    barrier = threading.Barrier(8)

    def create():
        try:
            barrier.wait()
            return store.open_case(tmp_path, "Same", "Description", case_id="same-id")
        except BaseException as exc:
            return exc

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: create(), range(8)))

    successes = [result for result in results if isinstance(result, dict)]
    failures = [result for result in results if isinstance(result, BaseException)]
    assert len(successes) == 1
    assert len(failures) == 7
    assert all(isinstance(error, FileExistsError) for error in failures)
    assert store.load_case(tmp_path, "same-id")["revision"] == 1


def test_blackboard_promotion_is_atomic_and_idempotent(tmp_path):
    store.open_case(tmp_path, "Board", "Description", case_id="board")
    entry = blackboard.add_entry(tmp_path, "board", "Promote me", tags=["x"])

    first = blackboard.promote_entry(tmp_path, "board", entry["id"], "observation", 0.7)
    second = blackboard.promote_entry(tmp_path, "board", entry["id"], "observation", 0.7)

    case = store.load_case(tmp_path, "board")
    assert first["node"]["id"] == second["node"]["id"]
    assert len([node for node in case["nodes"] if node.get("metadata", {}).get("blackboard_entry_id") == entry["id"]]) == 1
    assert case["blackboard"][0]["status"] == "promoted"


def test_blackboard_promotion_uses_store_node_argument_order(tmp_path):
    store.open_case(tmp_path, "Board Order", "Description", case_id="board-order")
    entry = blackboard.add_entry(tmp_path, "board-order", "Promote as hypothesis", tags=["x"])

    promoted = blackboard.promote_entry(tmp_path, "board-order", entry["id"], "hypothesis", 0.7)

    node = promoted["node"]
    assert node["type"] == "hypothesis"
    assert node["content"] == "Promote as hypothesis"
    assert node["status"] == "open"
    assert node["confidence"] == 0.7
    assert node["source"] == "system"
    assert node["tags"] == ["x", "from-blackboard"]
    assert node["metadata"] == {"blackboard_entry_id": entry["id"]}


@pytest.mark.parametrize("node_type", ["bad", "open", "confirmed"])
def test_blackboard_promotion_validates_node_type_not_status(tmp_path, node_type):
    store.open_case(tmp_path, "Board Bad Type", "Description", case_id="board-bad-type")
    entry = blackboard.add_entry(tmp_path, "board-bad-type", "Promote badly")

    with pytest.raises(ValueError, match="Invalid node type"):
        blackboard.promote_entry(tmp_path, "board-bad-type", entry["id"], node_type, 0.7)


def test_completion_gate_uses_current_state_and_has_no_side_effects(tmp_path):
    make_closable_case(tmp_path, "gate")
    before = store.load_case(tmp_path, "gate")
    gate = proof.completion_gate(tmp_path, "gate")
    after = store.load_case(tmp_path, "gate")

    assert gate["allowed"] is True
    assert gate["current_proof"]["status"] == "passes"
    assert after["revision"] == before["revision"]
    assert after["proofs"] == []


def test_stale_persisted_proof_does_not_allow_current_blocked_gate(tmp_path):
    make_closable_case(tmp_path, "stale")
    persisted = proof.evaluate(tmp_path, "stale", "passes now")
    assert persisted["status"] == "passes"
    store.add_node(tmp_path, "stale", "question", "Still open?")

    gate = proof.completion_gate(tmp_path, "stale")

    assert gate["allowed"] is False
    assert any("open question" in blocker for blocker in gate["blockers"])


def test_close_recomputes_gate_inside_locked_mutation(tmp_path, monkeypatch):
    make_closable_case(tmp_path, "close-atomic")
    original_gate_from_case = proof.gate_from_case

    def inject_blocker(case, case_id, summary="completion gate"):
        case["nodes"].append(store.make_node("question", "Injected blocker"))
        return original_gate_from_case(case, case_id, summary)

    monkeypatch.setattr(proof, "gate_from_case", inject_blocker)

    with pytest.raises(ValueError, match="Completion gate blocks closure"):
        proof.close_case(tmp_path, "close-atomic", "done")

    case = store.load_case(tmp_path, "close-atomic")
    assert case["status"] == "open"
    assert all(node["content"] != "Injected blocker" for node in case["nodes"])


def test_closed_cases_reject_ordinary_mutations_centrally(tmp_path):
    make_closable_case(tmp_path, "closed")
    proof.close_case(tmp_path, "closed", "done")

    mutators = [
        lambda: store.add_node(tmp_path, "closed", "observation", "new"),
        lambda: actions.add_action(tmp_path, "closed", "new action"),
        lambda: blackboard.add_entry(tmp_path, "closed", "note"),
        lambda: coverage.add_item(tmp_path, "closed", "new area"),
        lambda: proof.evaluate(tmp_path, "closed", "new proof"),
    ]
    for mutate in mutators:
        with pytest.raises(store.ClosedCaseError):
            mutate()


def test_explicit_confirmation_requires_confirmed_hypothesis_and_confirmed_evidence(tmp_path):
    store.open_case(tmp_path, "Confirm", "Description", case_id="confirm")
    hypothesis = store.add_node(tmp_path, "confirm", "hypothesis", "Likely", status="verified", confidence=1.0)
    evidence = store.add_node(tmp_path, "confirm", "evidence", "Proof", status="confirmed", confidence=1.0)
    store.add_edge(tmp_path, "confirm", evidence["id"], hypothesis["id"], "supports")
    coverage.add_item(tmp_path, "confirm", "scope", status="complete")
    assert proof.completion_gate(tmp_path, "confirm")["allowed"] is False

    store.update_node(tmp_path, "confirm", hypothesis["id"], status="confirmed")
    store.update_node(tmp_path, "confirm", evidence["id"], status="verified")
    assert proof.completion_gate(tmp_path, "confirm")["allowed"] is False

    store.update_node(tmp_path, "confirm", evidence["id"], status="confirmed")
    assert proof.completion_gate(tmp_path, "confirm")["allowed"] is True


def test_filter_validation_and_enum_behavior(tmp_path):
    store.open_case(tmp_path, "Enums", "Description", case_id="enums")
    with pytest.raises(ValueError, match="Invalid node type"):
        graph.list_nodes(tmp_path, "enums", node_type="bad")
    with pytest.raises(ValueError, match="Invalid edge type"):
        graph.list_edges(tmp_path, "enums", edge_type="constrains")
    with pytest.raises(ValueError, match="Invalid action status"):
        actions.list_actions(tmp_path, "enums", status="planned")
    with pytest.raises(ValueError, match="Invalid coverage status"):
        coverage.add_item(tmp_path, "enums", "area", status="covered")
    with pytest.raises(ValueError, match="content must be a non-empty string"):
        store.add_node(tmp_path, "enums", "observation", " ")
    with pytest.raises(ValueError, match="metadata must be an object"):
        store.add_node(tmp_path, "enums", "observation", "x", metadata=[])


def test_max_actions_is_enforced(tmp_path):
    store.open_case(tmp_path, "Actions", "Description", case_id="actions", config={"max_actions": 1})
    actions.add_action(tmp_path, "actions", "first")
    with pytest.raises(ValueError, match="max_actions reached"):
        actions.add_action(tmp_path, "actions", "second")


def test_event_limit_returns_bounded_tail(tmp_path):
    store.open_case(tmp_path, "Events", "Description", case_id="events")
    for index in range(5):
        store.add_node(tmp_path, "events", "observation", f"node {index}")

    events = store.list_events(tmp_path, "events", limit=3)

    assert len(events) == 3
    assert [event["node_id"] for event in events] == [node["id"] for node in store.load_case(tmp_path, "events")["nodes"][-3:]]
    with pytest.raises(ValueError, match="limit must be positive"):
        store.list_events(tmp_path, "events", limit=0)
