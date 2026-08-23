from pathlib import Path
from typing import Any

from . import store


def _truncate(value: str, limit: int = 48) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _escape_mermaid(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("[", "&#91;")
        .replace("]", "&#93;")
        .replace("\n", "<br/>")
    )


def _markdown_list_text(value: str) -> str:
    return " ".join(value.splitlines())


def export_markdown(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    directory = store.case_dir(workspace, case_id)
    path = directory / "notes.md"

    active_hypotheses = [
        node for node in case["nodes"] if node["type"] == "hypothesis" and node["status"] == "open"
    ]
    evidence_nodes = [node for node in case["nodes"] if node["type"] == "evidence"]
    nodes_by_id = {node["id"]: node for node in case["nodes"]}
    actions = case.get("actions", [])

    lines = [
        f"# Case: {case['title']}",
        "",
        case["description"],
        "",
        "## Active Hypotheses",
    ]

    if active_hypotheses:
        lines.extend(
            f"- {_markdown_list_text(node['content'])} (confidence: {node['confidence']:.2f}, source: {node['source']})"
            for node in active_hypotheses
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Evidence"])
    if evidence_nodes:
        lines.extend(f"- {_markdown_list_text(node['content'])} (source: {node['source']})" for node in evidence_nodes)
    else:
        lines.append("- None")

    lines.extend(["", "## Key Relationships"])
    if case["edges"]:
        for edge in case["edges"]:
            from_node = nodes_by_id.get(edge["from_id"])
            to_node = nodes_by_id.get(edge["to_id"])
            from_text = _markdown_list_text(from_node["content"] if from_node else edge["from_id"])
            to_text = _markdown_list_text(to_node["content"] if to_node else edge["to_id"])
            edge_type = _markdown_list_text(edge["type"])
            relationship = f"- {from_text} -- {edge_type} --> {to_text}"
            if edge.get("rationale"):
                relationship += f" ({_markdown_list_text(edge['rationale'])})"
            lines.append(relationship)
    else:
        lines.append("- None")

    lines.extend(["", "## Actions"])
    if actions:
        for action in actions:
            lines.append(
                "- "
                f"id: {action['id']}; "
                f"description: {_markdown_list_text(action.get('description', ''))}; "
                f"assigned role: {_markdown_list_text(action.get('assigned_role', ''))}; "
                f"priority: {float(action.get('priority', 0.0)):.2f}; "
                f"status: {_markdown_list_text(action.get('status', 'pending'))}; "
                f"reason: {_markdown_list_text(action.get('reason', ''))}"
            )
    else:
        lines.append("- None")

    store._atomic_write_text(path, "\n".join(lines) + "\n")
    return {"case_id": case["id"], "path": str(path)}


def export_mermaid(
    workspace: str | Path | None,
    case_id: str,
    diagram: str = "full",
    focus_node_id: str | None = None,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    directory = store.case_dir(workspace, case_id)
    path = directory / "graph.mmd"

    nodes = case["nodes"]
    edges = case["edges"]

    if diagram not in {"full", "hypothesis-chain"}:
        raise ValueError("diagram must be one of: full, hypothesis-chain")
    if diagram == "hypothesis-chain" and focus_node_id is None:
        raise ValueError("focus_node_id is required for hypothesis-chain diagrams")

    if diagram == "hypothesis-chain" and focus_node_id is not None:
        store.find_node(case, focus_node_id)
        focused_edges = [
            edge
            for edge in case["edges"]
            if edge.get("from_id") == focus_node_id or edge.get("to_id") == focus_node_id
        ]
        focused_node_ids = {focus_node_id}
        for edge in focused_edges:
            focused_node_ids.add(edge["from_id"])
            focused_node_ids.add(edge["to_id"])
        nodes = [node for node in case["nodes"] if node["id"] in focused_node_ids]
        edges = focused_edges

    lines = ["graph LR"]
    for node in nodes:
        label = _escape_mermaid(_truncate(node["content"]))
        lines.append(f'    {node["id"]}["{label}"]')

    for edge in edges:
        label = _escape_mermaid(edge["type"])
        lines.append(f'    {edge["from_id"]} -- {label} --> {edge["to_id"]}')

    store._atomic_write_text(path, "\n".join(lines) + "\n")
    return {"case_id": case["id"], "path": str(path)}
