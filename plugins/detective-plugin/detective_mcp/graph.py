from collections import Counter, deque
from pathlib import Path
from typing import Any

from . import store


def _case(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    return store.load_case(workspace, case_id)


def graph_overview(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    nodes = case["nodes"]
    edges = case["edges"]
    by_type = dict(Counter(node["type"] for node in nodes))
    total_nodes = len(nodes)
    total_edges = len(edges)
    edge_node_ratio = round(total_edges / total_nodes, 2) if total_nodes else 0.0
    return {
        "case_id": case["id"],
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "by_type": by_type,
        "active_hypotheses": sum(1 for node in nodes if node["type"] == "hypothesis" and node["status"] == "open"),
        "open_questions": sum(1 for node in nodes if node["type"] == "question" and node["status"] == "open"),
        "graph_density": edge_node_ratio,
        "edge_node_ratio": edge_node_ratio,
    }


def list_nodes(
    workspace: str | Path | None,
    case_id: str,
    node_type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    case = _case(workspace, case_id)
    nodes = case["nodes"]
    if node_type is not None:
        nodes = [node for node in nodes if node["type"] == node_type]
    if status is not None:
        nodes = [node for node in nodes if node["status"] == status]
    if tag is not None:
        tag_needle = tag.lower()
        nodes = [node for node in nodes if any(tag_needle == node_tag.lower() for node_tag in node.get("tags", []))]
    if limit is not None:
        nodes = nodes[:limit]
    return nodes


def get_node(workspace: str | Path | None, case_id: str, node_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    return store.find_node(case, node_id)


def get_edge(workspace: str | Path | None, case_id: str, edge_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    return store.find_edge(case, edge_id)


def search_nodes(
    workspace: str | Path | None,
    case_id: str,
    query: str,
    types: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    case = _case(workspace, case_id)
    needle = query.lower()
    nodes = case["nodes"]
    if types is not None:
        nodes = [node for node in nodes if node["type"] in types]
    matches = [
        node
        for node in nodes
        if needle in node["content"].lower() or any(needle in tag.lower() for tag in node.get("tags", []))
    ]
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
    case = _case(workspace, case_id)
    edges = case["edges"]
    if edge_type is not None:
        edges = [edge for edge in edges if edge["type"] == edge_type]
    if from_id is not None:
        edges = [edge for edge in edges if edge["from_id"] == from_id]
    if to_id is not None:
        edges = [edge for edge in edges if edge["to_id"] == to_id]
    return edges


def neighbors(workspace: str | Path | None, case_id: str, node_id: str) -> dict[str, Any]:
    case = _case(workspace, case_id)
    node = store.find_node(case, node_id)
    incoming_edges = [edge for edge in case["edges"] if edge["to_id"] == node_id]
    outgoing_edges = [edge for edge in case["edges"] if edge["from_id"] == node_id]
    return {
        "node": node,
        "incoming_edges": incoming_edges,
        "outgoing_edges": outgoing_edges,
        "incoming_nodes": [store.find_node(case, edge["from_id"]) for edge in incoming_edges],
        "outgoing_nodes": [store.find_node(case, edge["to_id"]) for edge in outgoing_edges],
    }


def shortest_path(
    workspace: str | Path | None,
    case_id: str,
    from_id: str,
    to_id: str,
    undirected: bool = False,
) -> dict[str, Any]:
    case = _case(workspace, case_id)
    try:
        store.find_node(case, from_id)
        store.find_node(case, to_id)
    except KeyError:
        return {"nodes": [], "edges": [], "reason": "missing_endpoint"}

    adjacency: dict[str, list[tuple[str, dict[str, Any], bool]]] = {}
    for edge in case["edges"]:
        adjacency.setdefault(edge["from_id"], []).append((edge["to_id"], edge, False))
        if undirected:
            adjacency.setdefault(edge["to_id"], []).append((edge["from_id"], edge, True))

    queue: deque[str] = deque([from_id])
    visited = {from_id}
    previous: dict[str, tuple[str, dict[str, Any]]] = {}

    while queue:
        current = queue.popleft()
        if current == to_id:
            break
        for neighbor_id, edge, reversed_edge in adjacency.get(current, []):
            if neighbor_id in visited:
                continue
            visited.add(neighbor_id)
            edge_step = {
                **edge,
                "traversal_from_id": current,
                "traversal_to_id": neighbor_id,
                "reversed": reversed_edge,
            }
            previous[neighbor_id] = (current, edge_step)
            queue.append(neighbor_id)

    if to_id not in visited:
        return {"nodes": [], "edges": [], "reason": "no_path"}

    node_ids = [to_id]
    edges = []
    current = to_id
    while current != from_id:
        parent_id, edge = previous[current]
        node_ids.append(parent_id)
        edges.append(edge)
        current = parent_id

    node_ids.reverse()
    edges.reverse()
    return {
        "nodes": [store.find_node(case, node_id) for node_id in node_ids],
        "edges": edges,
        "reason": "found",
    }
