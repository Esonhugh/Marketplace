from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import actions, blackboard, coverage, exports, graph, ooda, proof, store

mcp = FastMCP("detective")


@mcp.tool()
def detective_open_case(
    title: str,
    description: str,
    case_id: str | None = None,
    workspace: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    return store.open_case(workspace, title, description, case_id=case_id, config=config)


@mcp.tool()
def detective_load_case(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    return {
        "case_id": case["id"],
        "title": case["title"],
        "description": case["description"],
        "total_nodes": len(case["nodes"]),
        "total_edges": len(case["edges"]),
        "updated_at": case["updated_at"],
    }


@mcp.tool()
def detective_graph_overview(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return graph.graph_overview(workspace, case_id)


@mcp.tool()
def detective_case_status(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return store.get_case_status(workspace, case_id)


@mcp.tool()
def detective_transition_phase(case_id: str, phase: str, reason: str = "", session: str | None = None, workspace: str | Path | None = None) -> dict[str, Any]:
    return ooda.transition_phase(workspace, case_id, phase, reason, session)


@mcp.tool()
def detective_add_intent(case_id: str, intent: str, phase: str | None = None, created_by: str = "system", metadata: dict[str, Any] | None = None, workspace: str | Path | None = None) -> dict[str, Any]:
    return ooda.add_intent(workspace, case_id, intent, phase, created_by, metadata)


@mcp.tool()
def detective_list_intents(case_id: str, phase: str | None = None, status: str | None = None, workspace: str | Path | None = None) -> list[dict[str, Any]]:
    return ooda.list_intents(workspace, case_id, phase, status)


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
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return store.add_node(
        workspace,
        case_id,
        node_type=type,
        content=content,
        status=status,
        confidence=confidence,
        source=source,
        tags=tags,
        created_by=created_by,
        metadata=metadata,
    )


@mcp.tool()
def detective_update_node(
    case_id: str,
    node_id: str,
    content: str | None = None,
    status: str | None = None,
    confidence: float | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return store.update_node(
        workspace,
        case_id,
        node_id,
        content=content,
        status=status,
        confidence=confidence,
        tags=tags,
        metadata=metadata,
    )


@mcp.tool()
def detective_delete_node(case_id: str, node_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return store.delete_node(workspace, case_id, node_id)


@mcp.tool()
def detective_get_node(case_id: str, node_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return graph.get_node(workspace, case_id, node_id)


@mcp.tool()
def detective_list_nodes(
    case_id: str,
    type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
    workspace: str | Path | None = None,
) -> list[dict[str, Any]]:
    return graph.list_nodes(workspace, case_id, node_type=type, status=status, tag=tag, limit=limit)


@mcp.tool()
def detective_search_nodes(
    case_id: str,
    query: str,
    types: list[str] | None = None,
    limit: int | None = None,
    workspace: str | Path | None = None,
) -> list[dict[str, Any]]:
    return graph.search_nodes(workspace, case_id, query=query, types=types, limit=limit)


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
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return store.add_edge(
        workspace,
        case_id,
        from_id,
        to_id,
        edge_type=type,
        confidence=confidence,
        rationale=rationale,
        created_by=created_by,
        metadata=metadata,
    )


@mcp.tool()
def detective_get_edge(case_id: str, edge_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return graph.get_edge(workspace, case_id, edge_id)


@mcp.tool()
def detective_update_edge(
    case_id: str,
    edge_id: str,
    type: str | None = None,
    confidence: float | None = None,
    rationale: str | None = None,
    metadata: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return store.update_edge(
        workspace,
        case_id,
        edge_id,
        edge_type=type,
        confidence=confidence,
        rationale=rationale,
        metadata=metadata,
    )


@mcp.tool()
def detective_delete_edge(case_id: str, edge_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return store.delete_edge(workspace, case_id, edge_id)


@mcp.tool()
def detective_list_edges(
    case_id: str,
    type: str | None = None,
    from_id: str | None = None,
    to_id: str | None = None,
    workspace: str | Path | None = None,
) -> list[dict[str, Any]]:
    return graph.list_edges(workspace, case_id, edge_type=type, from_id=from_id, to_id=to_id)


@mcp.tool()
def detective_neighbors(case_id: str, node_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return graph.neighbors(workspace, case_id, node_id)


@mcp.tool()
def detective_shortest_path(
    case_id: str,
    from_id: str,
    to_id: str,
    undirected: bool = False,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return graph.shortest_path(workspace, case_id, from_id, to_id, undirected=undirected)


@mcp.tool()
def detective_export_markdown(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return exports.export_markdown(workspace, case_id)


@mcp.tool()
def detective_export_mermaid(
    case_id: str,
    diagram: str = "full",
    focus_node_id: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return exports.export_mermaid(workspace, case_id, diagram, focus_node_id)


@mcp.tool()
def detective_add_action(case_id: str, description: str, assigned_role: str = "agent", priority: float = 0.5, reason: str = "", workspace: str | Path | None = None) -> dict[str, Any]:
    return actions.add_action(workspace, case_id, description, assigned_role, priority, reason)


@mcp.tool()
def detective_update_action(case_id: str, action_id: str, status: str | None = None, result: str | None = None, metadata: dict[str, Any] | None = None, workspace: str | Path | None = None) -> dict[str, Any]:
    return actions.update_action(workspace, case_id, action_id, status, result, metadata)


@mcp.tool()
def detective_list_actions(case_id: str, status: str | None = None, workspace: str | Path | None = None) -> list[dict[str, Any]]:
    return actions.list_actions(workspace, case_id, status)


@mcp.tool()
def detective_add_checkpoint(case_id: str, summary: str, action_id: str | None = None, created_by: str = "system", metadata: dict[str, Any] | None = None, workspace: str | Path | None = None) -> dict[str, Any]:
    return actions.add_checkpoint(workspace, case_id, summary, action_id, created_by, metadata)


@mcp.tool()
def detective_blackboard_add(case_id: str, content: str, kind: str = "note", tags: list[str] | None = None, created_by: str = "system", workspace: str | Path | None = None) -> dict[str, Any]:
    return blackboard.add_entry(workspace, case_id, content, kind, tags, created_by)


@mcp.tool()
def detective_blackboard_list(case_id: str, status: str | None = None, kind: str | None = None, workspace: str | Path | None = None) -> list[dict[str, Any]]:
    return blackboard.list_entries(workspace, case_id, status, kind)


@mcp.tool()
def detective_blackboard_update(case_id: str, entry_id: str, content: str | None = None, status: str | None = None, tags: list[str] | None = None, workspace: str | Path | None = None) -> dict[str, Any]:
    return blackboard.update_entry(workspace, case_id, entry_id, content, status, tags)


@mcp.tool()
def detective_blackboard_promote(case_id: str, entry_id: str, node_type: str = "observation", confidence: float = 0.6, workspace: str | Path | None = None) -> dict[str, Any]:
    return blackboard.promote_entry(workspace, case_id, entry_id, node_type, confidence)


@mcp.tool()
def detective_coverage_add(case_id: str, area: str, status: str = "planned", notes: str = "", workspace: str | Path | None = None) -> dict[str, Any]:
    return coverage.add_item(workspace, case_id, area, status, notes)


@mcp.tool()
def detective_coverage_update(case_id: str, coverage_id: str, status: str | None = None, notes: str | None = None, workspace: str | Path | None = None) -> dict[str, Any]:
    return coverage.update_item(workspace, case_id, coverage_id, status, notes)


@mcp.tool()
def detective_coverage_status(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return coverage.status(workspace, case_id)


@mcp.tool()
def detective_evaluate_proof(case_id: str, summary: str = "", workspace: str | Path | None = None) -> dict[str, Any]:
    return proof.evaluate(workspace, case_id, summary)


@mcp.tool()
def detective_completion_gate(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return proof.completion_gate(workspace, case_id)


@mcp.tool()
def detective_close_case(case_id: str, summary: str, approved_by: str = "system", force: bool = False, workspace: str | Path | None = None) -> dict[str, Any]:
    return proof.close_case(workspace, case_id, summary, approved_by, force)


@mcp.tool()
def detective_list_events(case_id: str, limit: int | None = None, workspace: str | Path | None = None) -> list[dict[str, Any]]:
    return store.list_events(workspace, case_id, limit)


if __name__ == "__main__":
    mcp.run()
