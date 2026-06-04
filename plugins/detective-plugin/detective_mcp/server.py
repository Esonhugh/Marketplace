from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import exports, graph, scheduler, signals, store

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
def detective_save_case(case_id: str, workspace: str | Path | None = None) -> dict[str, str]:
    case = store.load_case(workspace, case_id)
    return store.save_case(workspace, case)


@mcp.tool()
def detective_graph_overview(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
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
def detective_record_direction_attempt(
    case_id: str,
    description: str,
    target_node_ids: list[str],
    new_evidence_count: int,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return scheduler.record_direction_attempt(workspace, case_id, description, target_node_ids, new_evidence_count)


@mcp.tool()
def detective_add_next_action(
    case_id: str,
    description: str,
    assigned_role: str,
    priority: float,
    reason: str,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return scheduler.add_next_action(workspace, case_id, description, assigned_role, priority, reason)


@mcp.tool()
def detective_score_candidate_actions(
    case_id: str,
    candidates: list[dict[str, Any]],
    workspace: str | Path | None = None,
) -> list[dict[str, Any]]:
    return scheduler.score_candidate_actions(workspace, case_id, candidates)


@mcp.tool()
def detective_apply_user_guidance(
    case_id: str,
    guidance_type: str,
    content: str,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return scheduler.apply_user_guidance(workspace, case_id, guidance_type, content)


@mcp.tool()
def detective_convergence_status(case_id: str, workspace: str | Path | None = None) -> dict[str, Any]:
    return signals.convergence_status(workspace, case_id)


@mcp.tool()
def detective_deadlock_status(
    case_id: str,
    scored_actions: list[dict[str, Any]],
    recent_new_nodes: int = 0,
    recent_new_edges: int = 0,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    return signals.deadlock_status(workspace, case_id, scored_actions, recent_new_nodes, recent_new_edges)


if __name__ == "__main__":
    mcp.run()
