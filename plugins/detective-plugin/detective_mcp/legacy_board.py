import json
import time
import uuid
from pathlib import Path


def _new_id():
    return uuid.uuid4().hex[:8]


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def init_case(title: str, description: str) -> dict:
    return {
        "id": _new_id(),
        "title": title,
        "description": description,
        "created_at": _now(),
        "updated_at": _now(),
        "phase": "opening",
        "fragments": [],
        "threads": [],
        "actions_history": [],
        "config": {
            "checkpoint_interval": 5,
            "max_actions": 50,
            "confidence_threshold_confirm": 0.85,
            "confidence_threshold_eliminate": 0.15,
        },
    }


def add_fragment(board: dict, fragment: dict) -> dict:
    fragment.setdefault("id", _new_id())
    fragment.setdefault("created_at", _now())
    fragment.setdefault("maturity", "raw")
    fragment.setdefault("role", "observation")
    fragment.setdefault("confidence", 0.5)
    fragment.setdefault("source", "system")
    fragment.setdefault("metadata", {})
    board["fragments"].append(fragment)
    board["updated_at"] = _now()
    return fragment


def add_thread(board: dict, thread: dict) -> dict:
    thread.setdefault("id", _new_id())
    thread.setdefault("created_at", _now())
    required = {"from_id", "to_id", "type"}
    if not required.issubset(thread.keys()):
        raise ValueError(f"Thread requires fields: {required}")
    if thread["type"] not in ("supports", "contradicts", "derives", "eliminates", "requires"):
        raise ValueError(f"Invalid thread type: {thread['type']}")
    board["threads"].append(thread)
    board["updated_at"] = _now()
    return thread


def evolve_fragment(board: dict, fragment_id: str, new_maturity: str) -> bool:
    maturity_order = ["raw", "clue", "evidence", "anchor"]
    for fragment in board["fragments"]:
        if fragment["id"] == fragment_id:
            current_idx = maturity_order.index(fragment["maturity"])
            new_idx = maturity_order.index(new_maturity)
            if new_idx > current_idx:
                fragment["maturity"] = new_maturity
                fragment["evolved_at"] = _now()
                board["updated_at"] = _now()
                return True
            return False
    return False


def eliminate_fragment(board: dict, fragment_id: str, reason: str) -> bool:
    for fragment in board["fragments"]:
        if fragment["id"] == fragment_id:
            fragment["status"] = "eliminated"
            fragment["elimination_reason"] = reason
            fragment["eliminated_at"] = _now()
            board["updated_at"] = _now()
            return True
    return False


def get_active_hypotheses(board: dict) -> list:
    return [
        fragment for fragment in board["fragments"]
        if fragment["role"] == "hypothesis" and fragment.get("status") != "eliminated"
    ]


def get_fragments_by_role(board: dict, role: str) -> list:
    return [fragment for fragment in board["fragments"] if fragment["role"] == role]


def get_threads_for(board: dict, fragment_id: str) -> dict:
    incoming = [thread for thread in board["threads"] if thread["to_id"] == fragment_id]
    outgoing = [thread for thread in board["threads"] if thread["from_id"] == fragment_id]
    return {"incoming": incoming, "outgoing": outgoing}


def board_summary(board: dict) -> dict:
    fragments = board["fragments"]
    by_maturity = {}
    for fragment in fragments:
        maturity = fragment["maturity"]
        by_maturity[maturity] = by_maturity.get(maturity, 0) + 1
    by_role = {}
    for fragment in fragments:
        role = fragment["role"]
        by_role[role] = by_role.get(role, 0) + 1
    active_hypotheses = get_active_hypotheses(board)
    eliminated = [fragment for fragment in fragments if fragment.get("status") == "eliminated"]
    return {
        "case_id": board["id"],
        "title": board["title"],
        "phase": board["phase"],
        "total_fragments": len(fragments),
        "total_threads": len(board["threads"]),
        "by_maturity": by_maturity,
        "by_role": by_role,
        "active_hypotheses": len(active_hypotheses),
        "eliminated": len(eliminated),
        "actions_taken": len(board["actions_history"]),
    }


def export_dot(board: dict) -> str:
    lines = ['digraph CaseBoard {', '  rankdir=LR;', '  node [shape=box];']
    for fragment in board["fragments"]:
        fragment_id = fragment["id"]
        content = fragment.get("content", "")[:20]
        if fragment.get("status") == "eliminated":
            node_attrs = 'style=dashed, color=gray'
        elif fragment["role"] == "hypothesis":
            node_attrs = f'color=blue, label="{fragment_id}\\n[H] {content}"'
        elif fragment["role"] == "constraint":
            node_attrs = f'color=red, label="{fragment_id}\\n[C] {content}"'
        else:
            maturity = fragment["maturity"][0].upper()
            node_attrs = f'label="{fragment_id}\\n[{maturity}] {content}"'
        lines.append(f'  "{fragment_id}" [{node_attrs}];')
    for thread in board["threads"]:
        edge_style = ""
        if thread["type"] == "contradicts":
            edge_style = ' [color=red, style=dashed]'
        elif thread["type"] == "eliminates":
            edge_style = ' [color=red]'
        elif thread["type"] == "supports":
            edge_style = ' [color=green]'
        lines.append(f'  "{thread["from_id"]}" -> "{thread["to_id"]}"{edge_style};')
    lines.append('}')
    return '\n'.join(lines)


def load_board(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_board(board: dict, path: str):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
