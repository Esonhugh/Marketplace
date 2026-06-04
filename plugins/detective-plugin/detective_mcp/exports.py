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

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"case_id": case["id"], "path": str(path)}


def export_mermaid(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    directory = store.case_dir(workspace, case_id)
    path = directory / "graph.mmd"

    lines = ["graph LR"]
    for node in case["nodes"]:
        label = _escape_mermaid(_truncate(node["content"]))
        lines.append(f'    {node["id"]}["{label}"]')

    for edge in case["edges"]:
        label = _escape_mermaid(edge["type"])
        lines.append(f'    {edge["from_id"]} -- {label} --> {edge["to_id"]}')

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"case_id": case["id"], "path": str(path)}
