import json

from detective_mcp import scheduler, store


def _event_records(workspace, case_id):
    events = workspace / ".detective" / "cases" / case_id / "events.jsonl"
    return [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]


def test_new_case_has_scheduler_state(tmp_path):
    store.open_case(tmp_path, "Scheduler Case", "Description", case_id="scheduler-case")

    case = store.load_case(tmp_path, "scheduler-case")

    assert case["scheduler"] == {
        "attempted_directions": [],
        "next_actions": [],
    }
    assert case["config"]["autonomy"] == "full_auto"
    assert case["config"]["user_override_policy"] == "always_priority"
    assert case["config"]["deadlock_score_threshold"] == 0.3
    assert case["config"]["confidence_threshold_confirm"] == 0.85
    assert case["config"]["confidence_threshold_eliminate"] == 0.15



def test_record_attempted_direction_marks_cold_after_three_empty_attempts(tmp_path):
    store.open_case(tmp_path, "Cold Case", "Description", case_id="cold-case")
    node = store.add_node(tmp_path, "cold-case", "hypothesis", "Maybe cache issue")

    first = scheduler.record_direction_attempt(
        tmp_path,
        "cold-case",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )
    second = scheduler.record_direction_attempt(
        tmp_path,
        "cold-case",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )
    third = scheduler.record_direction_attempt(
        tmp_path,
        "cold-case",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )

    assert first["attempts"] == 1
    assert second["attempts"] == 2
    assert third["attempts"] == 3
    assert third["status"] == "cold"



def test_record_attempted_direction_accumulates_new_evidence_count(tmp_path):
    store.open_case(tmp_path, "Evidence Count", "Description", case_id="evidence-count")
    node = store.add_node(tmp_path, "evidence-count", "hypothesis", "Maybe cache issue")

    first = scheduler.record_direction_attempt(
        tmp_path,
        "evidence-count",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=2,
    )
    second = scheduler.record_direction_attempt(
        tmp_path,
        "evidence-count",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=3,
    )

    assert first["new_evidence_count"] == 2
    assert second["new_evidence_count"] == 5



def test_record_attempted_direction_stays_open_when_earlier_attempt_found_evidence(tmp_path):
    store.open_case(tmp_path, "Mixed Evidence", "Description", case_id="mixed-evidence")
    node = store.add_node(tmp_path, "mixed-evidence", "hypothesis", "Maybe cache issue")

    scheduler.record_direction_attempt(
        tmp_path,
        "mixed-evidence",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=1,
    )
    scheduler.record_direction_attempt(
        tmp_path,
        "mixed-evidence",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )
    third = scheduler.record_direction_attempt(
        tmp_path,
        "mixed-evidence",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )

    assert third["attempts"] == 3
    assert third["new_evidence_count"] == 1
    assert third["status"] == "open"



def test_record_attempted_direction_logs_direction_attempted_event(tmp_path):
    store.open_case(tmp_path, "Attempt Event", "Description", case_id="attempt-event")
    node = store.add_node(tmp_path, "attempt-event", "hypothesis", "Maybe cache issue")

    direction = scheduler.record_direction_attempt(
        tmp_path,
        "attempt-event",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )

    records = _event_records(tmp_path, "attempt-event")
    assert records[-1]["type"] == "direction_attempted"
    assert records[-1]["case_id"] == "attempt-event"
    assert records[-1]["direction_id"] == direction["id"]



def test_record_attempted_direction_persists_sorted_target_node_ids(tmp_path):
    store.open_case(tmp_path, "Sorted Targets", "Description", case_id="sorted-targets")
    first_node = store.add_node(tmp_path, "sorted-targets", "hypothesis", "Maybe cache issue")
    second_node = store.add_node(tmp_path, "sorted-targets", "evidence", "Stale entry")

    direction = scheduler.record_direction_attempt(
        tmp_path,
        "sorted-targets",
        description="Investigate cache issue",
        target_node_ids=[second_node["id"], first_node["id"]],
        new_evidence_count=0,
    )

    case = store.load_case(tmp_path, "sorted-targets")
    stored = case["scheduler"]["attempted_directions"][0]
    assert direction["target_node_ids"] == sorted([first_node["id"], second_node["id"]])
    assert stored["target_node_ids"] == sorted([first_node["id"], second_node["id"]])



def test_record_attempted_direction_sets_timestamp_fields(tmp_path):
    store.open_case(tmp_path, "Direction Times", "Description", case_id="direction-times")
    node = store.add_node(tmp_path, "direction-times", "hypothesis", "Maybe cache issue")

    first = scheduler.record_direction_attempt(
        tmp_path,
        "direction-times",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )
    second = scheduler.record_direction_attempt(
        tmp_path,
        "direction-times",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )

    assert first["created_at"]
    assert first["last_attempted_at"]
    assert second["created_at"] == first["created_at"]
    assert second["last_attempted_at"]



def test_add_next_action_sorts_by_priority(tmp_path):
    store.open_case(tmp_path, "Actions", "Description", case_id="actions")

    low = scheduler.add_next_action(tmp_path, "actions", "Low value", "evidence-hunter", 0.2, "cheap but narrow")
    high = scheduler.add_next_action(tmp_path, "actions", "High value", "contradiction-finder", 0.9, "tests leading theory")

    case = store.load_case(tmp_path, "actions")
    actions = case["scheduler"]["next_actions"]
    assert [action["id"] for action in actions] == [high["id"], low["id"]]
    assert actions[0]["status"] == "pending"



def test_record_attempted_direction_matches_same_targets_in_any_order(tmp_path):
    store.open_case(tmp_path, "Ordered Targets", "Description", case_id="ordered-targets")
    first_node = store.add_node(tmp_path, "ordered-targets", "hypothesis", "Maybe cache issue")
    second_node = store.add_node(tmp_path, "ordered-targets", "evidence", "Stale entry")

    first = scheduler.record_direction_attempt(
        tmp_path,
        "ordered-targets",
        description="Investigate cache issue",
        target_node_ids=[first_node["id"], second_node["id"]],
        new_evidence_count=0,
    )
    second = scheduler.record_direction_attempt(
        tmp_path,
        "ordered-targets",
        description="Investigate cache issue",
        target_node_ids=[second_node["id"], first_node["id"]],
        new_evidence_count=0,
    )

    case = store.load_case(tmp_path, "ordered-targets")
    directions = case["scheduler"]["attempted_directions"]
    assert first["id"] == second["id"]
    assert second["attempts"] == 2
    assert len(directions) == 1



def test_record_attempted_direction_with_new_evidence_stays_open(tmp_path):
    store.open_case(tmp_path, "Warm Case", "Description", case_id="warm-case")
    node = store.add_node(tmp_path, "warm-case", "hypothesis", "Maybe cache issue")

    for _ in range(3):
        result = scheduler.record_direction_attempt(
            tmp_path,
            "warm-case",
            description="Investigate cache issue",
            target_node_ids=[node["id"]],
            new_evidence_count=1,
        )

    assert result["attempts"] == 3
    assert result["status"] == "open"



def test_add_next_action_stores_float_priority_and_logs_event(tmp_path):
    store.open_case(tmp_path, "Logged Actions", "Description", case_id="logged-actions")

    action = scheduler.add_next_action(
        tmp_path,
        "logged-actions",
        "Check proxy path",
        "evidence-hunter",
        1,
        "highest leverage next check",
    )

    case = store.load_case(tmp_path, "logged-actions")
    stored = case["scheduler"]["next_actions"][0]
    records = _event_records(tmp_path, "logged-actions")

    assert stored["description"] == "Check proxy path"
    assert stored["assigned_role"] == "evidence-hunter"
    assert stored["reason"] == "highest leverage next check"
    assert stored["created_at"]
    assert "updated_at" not in stored
    assert isinstance(stored["priority"], float)
    assert stored["priority"] == 1.0
    assert action["priority"] == 1.0
    assert records[-1]["type"] == "next_action_added"
