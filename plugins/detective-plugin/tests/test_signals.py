import importlib

import pytest

from detective_mcp import store


def _signals_module():
    try:
        return importlib.import_module("detective_mcp.signals")
    except ModuleNotFoundError as exc:
        pytest.fail(f"detective_mcp.signals module is missing: {exc}")


def open_case(tmp_path, case_id: str, config: dict | None = None) -> str:
    store.open_case(tmp_path, f"Case {case_id}", "Description", case_id=case_id, config=config)
    return case_id


def test_convergence_false_when_open_question_blocks_confirmed_hypothesis(tmp_path):
    case_id = open_case(tmp_path, "blocking-question")
    evidence = store.add_node(tmp_path, case_id, "evidence", "Verified log line", confidence=1.0, source="file")
    confirmed = store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Database saturation caused the outage",
        confidence=0.9,
        source="agent",
    )
    question = store.add_node(tmp_path, case_id, "question", "Did saturation start before the alert?", source="agent")
    store.add_edge(tmp_path, case_id, evidence["id"], confirmed["id"], "supports")
    store.add_edge(tmp_path, case_id, question["id"], confirmed["id"], "requires")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["case_id"] == case_id
    assert result["converged"] is False
    assert [item["id"] for item in result["blocking_questions"]] == [question["id"]]
    assert "1 blocking open question" in result["reason"]
    assert result["recommendation"] == "continue-investigation"


def test_convergence_true_with_supported_confirmed_hypothesis_and_rejected_alternative(tmp_path):
    case_id = open_case(tmp_path, "supported-confirmed")
    evidence = store.add_node(tmp_path, case_id, "evidence", "Trace confirms rollout timing", confidence=1.0, source="file")
    confirmed = store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Rollout caused the regression",
        confidence=0.92,
        source="agent",
    )
    store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Traffic spike caused the regression",
        status="rejected",
        confidence=0.1,
        source="agent",
    )
    store.add_edge(tmp_path, case_id, evidence["id"], confirmed["id"], "supports")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["converged"] is True
    assert [item["id"] for item in result["confirmed_hypotheses"]] == [confirmed["id"]]
    assert result["alternatives_open"] == []
    assert result["blocking_questions"] == []
    assert result["recommendation"] == "close-case"


def test_convergence_false_when_confirmed_hypothesis_has_no_direct_evidence_support(tmp_path):
    case_id = open_case(tmp_path, "no-direct-support")
    observation = store.add_node(tmp_path, case_id, "observation", "Metrics regressed after deploy", confidence=0.9, source="tool")
    confirmed = store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Deploy introduced a bad timeout",
        confidence=0.9,
        source="agent",
    )
    store.add_edge(tmp_path, case_id, observation["id"], confirmed["id"], "supports")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["converged"] is False
    assert result["confirmed_hypotheses"] == []
    assert result["recommendation"] == "continue-investigation"


def test_convergence_false_when_active_alternative_remains_above_eliminate_threshold(tmp_path):
    case_id = open_case(tmp_path, "active-alternative")
    evidence = store.add_node(tmp_path, case_id, "evidence", "Exception points to cache", confidence=1.0, source="file")
    confirmed = store.add_node(tmp_path, case_id, "hypothesis", "Cache invalidation failed", confidence=0.9, source="agent")
    alternative = store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Database pool exhaustion caused the issue",
        confidence=0.4,
        source="agent",
    )
    store.add_edge(tmp_path, case_id, evidence["id"], confirmed["id"], "supports")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["converged"] is False
    assert [item["id"] for item in result["alternatives_open"]] == [alternative["id"]]
    assert result["recommendation"] == "continue-investigation"


def test_convergence_false_when_unsupported_high_confidence_hypothesis_remains_open(tmp_path):
    case_id = open_case(tmp_path, "unsupported-high-confidence-alternative")
    evidence = store.add_node(tmp_path, case_id, "evidence", "Trace confirms the cache failure", confidence=1.0, source="file")
    supported = store.add_node(tmp_path, case_id, "hypothesis", "Cache invalidation failed", confidence=0.9, source="agent")
    unsupported = store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Database pool exhaustion caused the issue",
        confidence=0.91,
        source="agent",
    )
    store.add_edge(tmp_path, case_id, evidence["id"], supported["id"], "supports")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["converged"] is False
    assert [item["id"] for item in result["confirmed_hypotheses"]] == [supported["id"]]
    assert [item["id"] for item in result["alternatives_open"]] == [unsupported["id"]]
    assert result["recommendation"] == "continue-investigation"


def test_question_requiring_unsupported_high_confidence_hypothesis_does_not_block_closure(tmp_path):
    case_id = open_case(tmp_path, "unsupported-required-question")
    evidence = store.add_node(tmp_path, case_id, "evidence", "Trace confirms the cache failure", confidence=1.0, source="file")
    supported = store.add_node(tmp_path, case_id, "hypothesis", "Cache invalidation failed", confidence=0.9, source="agent")
    unsupported = store.add_node(
        tmp_path,
        case_id,
        "hypothesis",
        "Database pool exhaustion caused the issue",
        confidence=0.91,
        source="agent",
    )
    question = store.add_node(tmp_path, case_id, "question", "Did the database pool exhaust first?", source="agent")
    store.add_edge(tmp_path, case_id, evidence["id"], supported["id"], "supports")
    store.add_edge(tmp_path, case_id, question["id"], unsupported["id"], "requires")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["converged"] is False
    assert [item["id"] for item in result["confirmed_hypotheses"]] == [supported["id"]]
    assert [item["id"] for item in result["alternatives_open"]] == [unsupported["id"]]
    assert result["blocking_questions"] == []
    assert result["recommendation"] == "continue-investigation"


def test_reverse_requires_from_confirmed_hypothesis_to_open_question_does_not_block_convergence(tmp_path):
    case_id = open_case(tmp_path, "reverse-requires-not-blocking")
    evidence = store.add_node(tmp_path, case_id, "evidence", "Trace confirms the cache failure", confidence=1.0, source="file")
    confirmed = store.add_node(tmp_path, case_id, "hypothesis", "Cache invalidation failed", confidence=0.9, source="agent")
    question = store.add_node(tmp_path, case_id, "question", "Should we notify the cache owner?", source="agent")
    store.add_edge(tmp_path, case_id, evidence["id"], confirmed["id"], "supports")
    store.add_edge(tmp_path, case_id, confirmed["id"], question["id"], "requires")

    result = _signals_module().convergence_status(tmp_path, case_id)

    assert result["converged"] is True
    assert result["blocking_questions"] == []
    assert [item["id"] for item in result["confirmed_hypotheses"]] == [confirmed["id"]]
    assert result["recommendation"] == "close-case"


def test_deadlock_true_when_all_scores_low_and_no_recent_graph_changes(tmp_path):
    case_id = open_case(tmp_path, "deadlock-true")

    result = _signals_module().deadlock_status(
        tmp_path,
        case_id,
        scored_actions=[
            {"description": "Gather one more log sample", "score": 0.2},
            {"description": "Ask another generic question", "score": 0.1},
        ],
    )

    assert result["case_id"] == case_id
    assert result["deadlocked"] is True
    assert "all candidate actions below" in result["reason"]
    assert result["recommendation"] == "discuss-case"


def test_deadlock_false_when_high_score_action_exists(tmp_path):
    case_id = open_case(tmp_path, "deadlock-high-score")

    result = _signals_module().deadlock_status(
        tmp_path,
        case_id,
        scored_actions=[
            {"description": "Inspect the deployment diff", "score": 0.8},
            {"description": "Collect another sample", "score": 0.1},
        ],
    )

    assert result["deadlocked"] is False
    assert result["recommendation"] == "continue-investigation"


def test_deadlock_false_when_recent_graph_changes_exist_even_if_scores_are_low(tmp_path):
    case_id = open_case(tmp_path, "deadlock-recent-changes")

    result = _signals_module().deadlock_status(
        tmp_path,
        case_id,
        scored_actions=[
            {"description": "Gather one more log sample", "score": 0.2},
            {"description": "Ask another generic question", "score": 0.1},
        ],
        recent_new_nodes=1,
        recent_new_edges=0,
    )

    assert result["deadlocked"] is False
    assert result["recommendation"] == "continue-investigation"
