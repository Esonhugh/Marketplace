import inspect
from pathlib import Path

import pytest

from detective_mcp import server


EXPECTED_TOOL_NAMES = {
    "detective_open_case",
    "detective_load_case",
    "detective_save_case",
    "detective_graph_overview",
    "detective_add_node",
    "detective_update_node",
    "detective_delete_node",
    "detective_get_node",
    "detective_list_nodes",
    "detective_search_nodes",
    "detective_add_edge",
    "detective_get_edge",
    "detective_update_edge",
    "detective_delete_edge",
    "detective_list_edges",
    "detective_neighbors",
    "detective_shortest_path",
    "detective_export_markdown",
    "detective_export_mermaid",
    "detective_record_direction_attempt",
    "detective_add_next_action",
    "detective_score_candidate_actions",
    "detective_apply_user_guidance",
    "detective_convergence_status",
    "detective_deadlock_status",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _input_schema(tool):
    if hasattr(tool, "inputSchema"):
        return tool.inputSchema
    if hasattr(tool, "input_schema"):
        return tool.input_schema
    if hasattr(tool, "model_dump"):
        dumped = tool.model_dump(by_alias=True)
        return dumped.get("inputSchema") or dumped.get("input_schema")
    raise AssertionError(f"Tool {tool!r} does not expose an input schema")


def _build_case(tmp_path):
    server.detective_open_case(
        title="Delegation Case",
        description="Exercise server wrappers",
        case_id="delegation-case",
        workspace=str(tmp_path),
    )
    observation = server.detective_add_node(
        case_id="delegation-case",
        type="observation",
        content="Observed behavior",
        source="user",
        tags=["alpha"],
        workspace=str(tmp_path),
    )
    evidence = server.detective_add_node(
        case_id="delegation-case",
        type="evidence",
        content="Evidence trail",
        source="file",
        tags=["alpha", "beta"],
        workspace=str(tmp_path),
    )
    hypothesis = server.detective_add_node(
        case_id="delegation-case",
        type="hypothesis",
        content="Possible explanation",
        source="agent",
        workspace=str(tmp_path),
    )
    support_edge = server.detective_add_edge(
        case_id="delegation-case",
        from_id=evidence["id"],
        to_id=hypothesis["id"],
        type="supports",
        workspace=str(tmp_path),
    )
    derive_edge = server.detective_add_edge(
        case_id="delegation-case",
        from_id=observation["id"],
        to_id=evidence["id"],
        type="derives",
        workspace=str(tmp_path),
    )
    return observation, evidence, hypothesis, support_edge, derive_edge


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


def test_server_load_case_returns_compact_summary(tmp_path):
    _build_case(tmp_path)

    loaded = server.detective_load_case("delegation-case", workspace=str(tmp_path))

    assert loaded["case_id"] == "delegation-case"
    assert loaded["title"] == "Delegation Case"
    assert loaded["description"] == "Exercise server wrappers"
    assert loaded["total_nodes"] == 3
    assert loaded["total_edges"] == 2
    assert "updated_at" in loaded


def test_server_list_and_search_wrappers_delegate_filters(tmp_path):
    observation, evidence, hypothesis, support_edge, derive_edge = _build_case(tmp_path)

    listed_nodes = server.detective_list_nodes("delegation-case", type="evidence", workspace=str(tmp_path))
    searched_nodes = server.detective_search_nodes("delegation-case", "alpha", workspace=str(tmp_path))
    listed_edges = server.detective_list_edges("delegation-case", type="supports", workspace=str(tmp_path))
    neighbors = server.detective_neighbors("delegation-case", evidence["id"], workspace=str(tmp_path))
    fetched_node = server.detective_get_node("delegation-case", evidence["id"], workspace=str(tmp_path))

    assert [node["id"] for node in listed_nodes] == [evidence["id"]]
    assert {node["id"] for node in searched_nodes} == {observation["id"], evidence["id"]}
    assert [edge["id"] for edge in listed_edges] == [support_edge["id"]]
    assert fetched_node["id"] == evidence["id"]
    assert [node["id"] for node in neighbors["incoming_nodes"]] == [observation["id"]]
    assert [node["id"] for node in neighbors["outgoing_nodes"]] == [hypothesis["id"]]
    assert [edge["id"] for edge in neighbors["incoming_edges"]] == [derive_edge["id"]]
    assert [edge["id"] for edge in neighbors["outgoing_edges"]] == [support_edge["id"]]


def test_server_update_node_and_save_case_work(tmp_path):
    observation, evidence, hypothesis, support_edge, derive_edge = _build_case(tmp_path)

    updated = server.detective_update_node(
        "delegation-case",
        evidence["id"],
        content="Evidence trail updated",
        status="verified",
        confidence=0.9,
        metadata={"reviewed": True},
        workspace=str(tmp_path),
    )
    case = server.detective_get_node("delegation-case", evidence["id"], workspace=str(tmp_path))
    saved = server.detective_save_case("delegation-case", workspace=str(tmp_path))

    assert updated["content"] == "Evidence trail updated"
    assert updated["status"] == "verified"
    assert updated["confidence"] == 0.9
    assert case["metadata"]["reviewed"] is True
    assert saved["case_id"] == "delegation-case"
    assert saved["status"] == "saved"


def test_server_delete_node_and_edge_wrappers_work(tmp_path):
    observation, evidence, hypothesis, support_edge, derive_edge = _build_case(tmp_path)

    fetched_edge = server.detective_get_edge("delegation-case", support_edge["id"], workspace=str(tmp_path))
    updated_edge = server.detective_update_edge(
        "delegation-case",
        support_edge["id"],
        type="contradicts",
        confidence=0.7,
        rationale="Contrary evidence",
        metadata={"reviewed": True},
        workspace=str(tmp_path),
    )
    deleted_edge = server.detective_delete_edge("delegation-case", derive_edge["id"], workspace=str(tmp_path))
    deleted_node = server.detective_delete_node("delegation-case", evidence["id"], workspace=str(tmp_path))
    remaining_edges = server.detective_list_edges("delegation-case", workspace=str(tmp_path))
    remaining_nodes = server.detective_list_nodes("delegation-case", workspace=str(tmp_path))

    assert fetched_edge["id"] == support_edge["id"]
    assert updated_edge["type"] == "contradicts"
    assert updated_edge["confidence"] == 0.7
    assert updated_edge["rationale"] == "Contrary evidence"
    assert updated_edge["metadata"]["reviewed"] is True
    assert deleted_edge["id"] == derive_edge["id"]
    assert deleted_node["id"] == evidence["id"]
    assert remaining_edges == []
    assert {node["id"] for node in remaining_nodes} == {observation["id"], hypothesis["id"]}


def test_server_scheduler_wrappers_delegate_to_helpers(tmp_path):
    server.detective_open_case("Scheduler Server", "Description", case_id="scheduler-server", workspace=str(tmp_path))
    target = server.detective_add_node(
        "scheduler-server",
        "hypothesis",
        "Cache branch may be stale",
        workspace=str(tmp_path),
    )

    direction = server.detective_record_direction_attempt(
        case_id="scheduler-server",
        description="Retry stale cache branch",
        target_node_ids=[target["id"]],
        new_evidence_count=0,
        workspace=str(tmp_path),
    )
    action = server.detective_add_next_action(
        case_id="scheduler-server",
        description="Inspect fresh deployment logs",
        assigned_role="evidence-hunter",
        priority=0.9,
        reason="Fresh evidence has high leverage",
        workspace=str(tmp_path),
    )
    scored = server.detective_score_candidate_actions(
        case_id="scheduler-server",
        candidates=[
            {
                "description": "Inspect fresh deployment logs",
                "target_node_ids": [target["id"]],
                "information_gain": 0.8,
                "feasibility": 0.9,
                "urgency": 0.7,
                "cost": 2,
            }
        ],
        workspace=str(tmp_path),
    )
    guidance = server.detective_apply_user_guidance(
        case_id="scheduler-server",
        guidance_type="constraint",
        content="Do not contact the suspect directly.",
        workspace=str(tmp_path),
    )

    assert direction["description"] == "Retry stale cache branch"
    assert direction["target_node_ids"] == [target["id"]]
    assert direction["attempts"] == 1
    assert action["description"] == "Inspect fresh deployment logs"
    assert action["assigned_role"] == "evidence-hunter"
    assert action["priority"] == 0.9
    assert scored == [
        {
            "description": "Inspect fresh deployment logs",
            "target_node_ids": [target["id"]],
            "information_gain": 0.8,
            "feasibility": 0.9,
            "urgency": 0.7,
            "cost": 2,
            "score": 0.252,
            "cold_direction": False,
        }
    ]
    assert guidance["case_id"] == "scheduler-server"
    assert guidance["policy"] == "user_guidance_has_priority"
    assert guidance["node"]["type"] == "constraint"
    assert guidance["node"]["metadata"]["guidance_type"] == "constraint"


def test_server_signal_wrappers_delegate_to_helpers(tmp_path):
    server.detective_open_case("Signals Server", "Description", case_id="signals-server", workspace=str(tmp_path))
    evidence = server.detective_add_node(
        "signals-server",
        "evidence",
        "Trace confirms rollout timing",
        confidence=1.0,
        source="file",
        workspace=str(tmp_path),
    )
    confirmed = server.detective_add_node(
        "signals-server",
        "hypothesis",
        "Rollout caused the regression",
        confidence=0.92,
        source="agent",
        workspace=str(tmp_path),
    )
    server.detective_add_edge(
        "signals-server",
        evidence["id"],
        confirmed["id"],
        "supports",
        workspace=str(tmp_path),
    )

    convergence = server.detective_convergence_status("signals-server", workspace=str(tmp_path))
    deadlock = server.detective_deadlock_status(
        case_id="signals-server",
        scored_actions=[{"description": "Ask another generic question", "score": 0.1}],
        recent_new_nodes=0,
        recent_new_edges=0,
        workspace=str(tmp_path),
    )

    assert convergence["converged"] is True
    assert convergence["confirmed_hypotheses"] == [
        {
            "id": confirmed["id"],
            "content": "Rollout caused the regression",
            "status": "open",
            "confidence": 0.92,
        }
    ]
    assert convergence["recommendation"] == "close-case"
    assert deadlock["deadlocked"] is True
    assert deadlock["recommendation"] == "discuss-case"


def test_scheduler_and_signal_wrapper_signatures_preserve_public_parameters():
    expected_signatures = {
        "detective_record_direction_attempt": [
            "case_id",
            "description",
            "target_node_ids",
            "new_evidence_count",
            "workspace",
        ],
        "detective_add_next_action": [
            "case_id",
            "description",
            "assigned_role",
            "priority",
            "reason",
            "workspace",
        ],
        "detective_score_candidate_actions": ["case_id", "candidates", "workspace"],
        "detective_apply_user_guidance": ["case_id", "guidance_type", "content", "workspace"],
        "detective_convergence_status": ["case_id", "workspace"],
        "detective_deadlock_status": [
            "case_id",
            "scored_actions",
            "recent_new_nodes",
            "recent_new_edges",
            "workspace",
        ],
    }

    for wrapper_name, expected_parameters in expected_signatures.items():
        assert list(inspect.signature(getattr(server, wrapper_name)).parameters) == expected_parameters


def test_server_exposes_stable_mcp_identity():
    assert server.mcp is not None
    assert getattr(server.mcp, "name", "detective") == "detective"


@pytest.mark.anyio
async def test_mcp_registers_expected_tools():
    tools = await server.mcp.list_tools()

    assert len(tools) == 25
    assert {tool.name for tool in tools} == EXPECTED_TOOL_NAMES


@pytest.mark.anyio
async def test_mcp_tool_schemas_expose_public_type_parameters():
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}

    for tool_name in [
        "detective_add_node",
        "detective_add_edge",
        "detective_update_edge",
        "detective_list_nodes",
        "detective_list_edges",
    ]:
        schema = _input_schema(tools[tool_name])
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "type" in schema["properties"]

    assert "case_id" in _input_schema(tools["detective_add_node"])["required"]
    assert "type" in _input_schema(tools["detective_add_node"])["required"]
    assert "content" in _input_schema(tools["detective_add_node"])["required"]
    assert "type" in _input_schema(tools["detective_add_edge"])["required"]
    assert "type" not in _input_schema(tools["detective_update_edge"]).get("required", [])
    assert "type" not in _input_schema(tools["detective_list_nodes"]).get("required", [])
    assert "type" not in _input_schema(tools["detective_list_edges"]).get("required", [])


@pytest.mark.anyio
async def test_mcp_tool_schemas_expose_scheduler_and_signal_public_parameters():
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}

    assert "target_node_ids" in _input_schema(tools["detective_record_direction_attempt"])["properties"]
    assert "target_node_ids" in _input_schema(tools["detective_record_direction_attempt"])["required"]
    assert "candidates" in _input_schema(tools["detective_score_candidate_actions"])["properties"]
    assert "candidates" in _input_schema(tools["detective_score_candidate_actions"])["required"]
    assert "scored_actions" in _input_schema(tools["detective_deadlock_status"])["properties"]
    assert "scored_actions" in _input_schema(tools["detective_deadlock_status"])["required"]
    assert "recent_new_nodes" not in _input_schema(tools["detective_deadlock_status"]).get("required", [])
    assert "recent_new_edges" not in _input_schema(tools["detective_deadlock_status"]).get("required", [])


@pytest.mark.anyio
async def test_mcp_call_tool_reports_missing_case_as_tool_error(tmp_path):
    with pytest.raises(Exception, match="missing-case|Case not found"):
        await server.mcp.call_tool(
            "detective_load_case",
            {"case_id": "missing-case", "workspace": str(tmp_path)},
        )
