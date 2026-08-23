import inspect
from pathlib import Path

import pytest

from detective_mcp import server


EXPECTED_TOOL_NAMES = {
    "detective_open_case",
    "detective_load_case",
    "detective_graph_overview",
    "detective_case_status",
    "detective_transition_phase",
    "detective_add_intent",
    "detective_list_intents",
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
    "detective_add_action",
    "detective_update_action",
    "detective_list_actions",
    "detective_add_checkpoint",
    "detective_blackboard_add",
    "detective_blackboard_list",
    "detective_blackboard_update",
    "detective_blackboard_promote",
    "detective_coverage_add",
    "detective_coverage_update",
    "detective_coverage_status",
    "detective_evaluate_proof",
    "detective_completion_gate",
    "detective_close_case",
    "detective_list_events",
}
REMOVED_TOOL_NAMES = {
    "detective_save_case",
    "detective_migration_status",
    "detective_migrate_case",
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
    server.detective_open_case("Delegation Case", "Exercise server wrappers", case_id="delegation-case", workspace=str(tmp_path))
    observation = server.detective_add_node("delegation-case", "observation", "Observed behavior", source="user", tags=["alpha"], workspace=str(tmp_path))
    evidence = server.detective_add_node("delegation-case", "evidence", "Evidence trail", source="file", tags=["alpha", "beta"], workspace=str(tmp_path))
    hypothesis = server.detective_add_node("delegation-case", "hypothesis", "Possible explanation", source="agent", workspace=str(tmp_path))
    support_edge = server.detective_add_edge("delegation-case", evidence["id"], hypothesis["id"], "supports", workspace=str(tmp_path))
    derive_edge = server.detective_add_edge("delegation-case", observation["id"], evidence["id"], "derives", workspace=str(tmp_path))
    return observation, evidence, hypothesis, support_edge, derive_edge


def test_server_tool_wrappers_create_and_query_case(tmp_path):
    opened = server.detective_open_case("Server Case", "Tool wrapper smoke test", case_id="server-case", workspace=str(tmp_path))
    observation = server.detective_add_node("server-case", "observation", "Observed behavior", source="user", workspace=str(tmp_path))
    hypothesis = server.detective_add_node("server-case", "hypothesis", "Possible explanation", source="agent", workspace=str(tmp_path))
    edge = server.detective_add_edge("server-case", observation["id"], hypothesis["id"], "supports", workspace=str(tmp_path))
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


def test_server_list_search_and_neighbors_delegate_filters(tmp_path):
    observation, evidence, hypothesis, support_edge, derive_edge = _build_case(tmp_path)
    assert [n["id"] for n in server.detective_list_nodes("delegation-case", type="evidence", workspace=str(tmp_path))] == [evidence["id"]]
    assert {n["id"] for n in server.detective_search_nodes("delegation-case", "alpha", workspace=str(tmp_path))} == {observation["id"], evidence["id"]}
    assert [e["id"] for e in server.detective_list_edges("delegation-case", type="supports", workspace=str(tmp_path))] == [support_edge["id"]]
    neighbors = server.detective_neighbors("delegation-case", evidence["id"], workspace=str(tmp_path))
    assert server.detective_get_node("delegation-case", evidence["id"], workspace=str(tmp_path))["id"] == evidence["id"]
    assert [node["id"] for node in neighbors["incoming_nodes"]] == [observation["id"]]
    assert [node["id"] for node in neighbors["outgoing_nodes"]] == [hypothesis["id"]]
    assert [edge["id"] for edge in neighbors["incoming_edges"]] == [derive_edge["id"]]
    assert [edge["id"] for edge in neighbors["outgoing_edges"]] == [support_edge["id"]]


def test_server_update_and_delete_wrappers_work(tmp_path):
    observation, evidence, hypothesis, support_edge, derive_edge = _build_case(tmp_path)
    updated = server.detective_update_node("delegation-case", evidence["id"], content="Evidence trail updated", status="verified", confidence=0.9, metadata={"reviewed": True}, workspace=str(tmp_path))
    fetched_edge = server.detective_get_edge("delegation-case", support_edge["id"], workspace=str(tmp_path))
    updated_edge = server.detective_update_edge("delegation-case", support_edge["id"], type="contradicts", confidence=0.7, rationale="Contrary evidence", metadata={"reviewed": True}, workspace=str(tmp_path))
    deleted_edge = server.detective_delete_edge("delegation-case", derive_edge["id"], workspace=str(tmp_path))
    deleted_node = server.detective_delete_node("delegation-case", evidence["id"], workspace=str(tmp_path))
    assert updated["status"] == "verified" and updated["metadata"]["reviewed"] is True
    assert fetched_edge["id"] == support_edge["id"]
    assert updated_edge["type"] == "contradicts" and updated_edge["metadata"]["reviewed"] is True
    assert deleted_edge["id"] == derive_edge["id"]
    assert deleted_node["id"] == evidence["id"]
    assert server.detective_list_edges("delegation-case", workspace=str(tmp_path)) == []
    assert {node["id"] for node in server.detective_list_nodes("delegation-case", workspace=str(tmp_path))} == {observation["id"], hypothesis["id"]}


def test_ooda_action_blackboard_coverage_proof_wrappers(tmp_path):
    server.detective_open_case("Flow", "Description", case_id="flow", workspace=str(tmp_path))
    phase = server.detective_transition_phase("flow", "orient", "sort evidence", workspace=str(tmp_path))
    intent = server.detective_add_intent("flow", "identify root cause", workspace=str(tmp_path))
    entry = server.detective_blackboard_add("flow", "maybe cache", tags=["cache"], workspace=str(tmp_path))
    promoted = server.detective_blackboard_promote("flow", entry["id"], "hypothesis", confidence=0.9, workspace=str(tmp_path))
    server.detective_update_node("flow", promoted["node"]["id"], status="confirmed", workspace=str(tmp_path))
    evidence = server.detective_add_node("flow", "evidence", "trace proves cache", status="confirmed", confidence=1.0, source="file", workspace=str(tmp_path))
    server.detective_add_edge("flow", evidence["id"], promoted["node"]["id"], "supports", workspace=str(tmp_path))
    action = server.detective_add_action("flow", "inspect trace", priority=0.8, workspace=str(tmp_path))
    server.detective_update_action("flow", action["id"], status="done", workspace=str(tmp_path))
    checkpoint = server.detective_add_checkpoint("flow", "trace inspected", action_id=action["id"], workspace=str(tmp_path))
    cov = server.detective_coverage_add("flow", "logs", status="complete", workspace=str(tmp_path))
    proof = server.detective_evaluate_proof("flow", "cache proof", workspace=str(tmp_path))
    gate = server.detective_completion_gate("flow", workspace=str(tmp_path))
    closed = server.detective_close_case("flow", "cache caused it", workspace=str(tmp_path))
    assert phase["phase"] == "orient"
    assert intent["intent"] == "identify root cause"
    assert promoted["entry"]["status"] == "promoted"
    assert checkpoint["action_id"] == action["id"]
    assert cov["status"] == "complete"
    assert proof["status"] == "passes"
    assert gate["allowed"] is True
    assert closed["status"] == "closed"


def test_public_wrapper_signatures_are_consistent():
    expected = {
        "detective_transition_phase": ["case_id", "phase", "reason", "session", "workspace"],
        "detective_add_action": ["case_id", "description", "assigned_role", "priority", "reason", "workspace"],
        "detective_evaluate_proof": ["case_id", "summary", "workspace"],
        "detective_close_case": ["case_id", "summary", "approved_by", "force", "workspace"],
    }
    for name, params in expected.items():
        assert list(inspect.signature(getattr(server, name)).parameters) == params


def test_removed_legacy_public_wrappers_do_not_exist():
    for name in REMOVED_TOOL_NAMES:
        assert not hasattr(server, name)


def test_server_exposes_stable_mcp_identity():
    assert server.mcp is not None
    assert getattr(server.mcp, "name", "detective") == "detective"


@pytest.mark.anyio
async def test_mcp_registers_exact_v04_tools():
    tools = await server.mcp.list_tools()
    assert len(tools) == len(EXPECTED_TOOL_NAMES)
    assert {tool.name for tool in tools} == EXPECTED_TOOL_NAMES
    assert not ({tool.name for tool in tools} & REMOVED_TOOL_NAMES)


@pytest.mark.anyio
async def test_mcp_tool_schemas_expose_public_type_parameters():
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}
    for tool_name in ["detective_add_node", "detective_add_edge", "detective_update_edge", "detective_list_nodes", "detective_list_edges"]:
        schema = _input_schema(tools[tool_name])
        assert schema["type"] == "object"
        assert "type" in schema["properties"]
    assert "type" in _input_schema(tools["detective_add_node"])["required"]
    assert "type" in _input_schema(tools["detective_add_edge"])["required"]
    assert "type" not in _input_schema(tools["detective_update_edge"]).get("required", [])


@pytest.mark.anyio
async def test_mcp_call_tool_reports_missing_case_as_tool_error(tmp_path):
    with pytest.raises(Exception, match="missing-case|Case not found"):
        await server.mcp.call_tool("detective_load_case", {"case_id": "missing-case", "workspace": str(tmp_path)})
