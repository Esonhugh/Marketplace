#!/usr/bin/env python3
"""CaseBoard state management — Fragment/Thread CRUD and graph operations.

Usage: python board.py <command> <case_file> [args...]

Commands:
  init <case_file> <title> <description>    Create a new case
  add-fragment <case_file> <json>           Add a Fragment to the board
  add-thread <case_file> <json>             Add a Thread (connection)
  evolve <case_file> <fragment_id> <new_maturity>  Promote fragment maturity
  eliminate <case_file> <fragment_id> <reason>     Eliminate a hypothesis
  status <case_file>                        Print board summary
  export-graph <case_file>                  Export as DOT graph
"""

import json
import sys
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
    for f in board["fragments"]:
        if f["id"] == fragment_id:
            current_idx = maturity_order.index(f["maturity"])
            new_idx = maturity_order.index(new_maturity)
            if new_idx > current_idx:
                f["maturity"] = new_maturity
                f["evolved_at"] = _now()
                board["updated_at"] = _now()
                return True
            return False
    return False


def eliminate_fragment(board: dict, fragment_id: str, reason: str) -> bool:
    for f in board["fragments"]:
        if f["id"] == fragment_id:
            f["status"] = "eliminated"
            f["elimination_reason"] = reason
            f["eliminated_at"] = _now()
            board["updated_at"] = _now()
            return True
    return False


def get_active_hypotheses(board: dict) -> list:
    return [
        f for f in board["fragments"]
        if f["role"] == "hypothesis"
        and f.get("status") != "eliminated"
    ]


def get_fragments_by_role(board: dict, role: str) -> list:
    return [f for f in board["fragments"] if f["role"] == role]


def get_threads_for(board: dict, fragment_id: str) -> dict:
    incoming = [t for t in board["threads"] if t["to_id"] == fragment_id]
    outgoing = [t for t in board["threads"] if t["from_id"] == fragment_id]
    return {"incoming": incoming, "outgoing": outgoing}


def board_summary(board: dict) -> dict:
    fragments = board["fragments"]
    by_maturity = {}
    for f in fragments:
        m = f["maturity"]
        by_maturity[m] = by_maturity.get(m, 0) + 1
    by_role = {}
    for f in fragments:
        r = f["role"]
        by_role[r] = by_role.get(r, 0) + 1
    active_hyp = get_active_hypotheses(board)
    eliminated = [f for f in fragments if f.get("status") == "eliminated"]
    return {
        "case_id": board["id"],
        "title": board["title"],
        "phase": board["phase"],
        "total_fragments": len(fragments),
        "total_threads": len(board["threads"]),
        "by_maturity": by_maturity,
        "by_role": by_role,
        "active_hypotheses": len(active_hyp),
        "eliminated": len(eliminated),
        "actions_taken": len(board["actions_history"]),
    }


def export_dot(board: dict) -> str:
    lines = ['digraph CaseBoard {', '  rankdir=LR;', '  node [shape=box];']
    for f in board["fragments"]:
        style = ""
        if f.get("status") == "eliminated":
            style = ', style=dashed, color=gray'
        elif f["role"] == "hypothesis":
            style = f', color=blue, label="{f["id"]}\\n[H] {f.get("content", "")[:20]}"'
        elif f["role"] == "constraint":
            style = f', color=red, label="{f["id"]}\\n[C] {f.get("content", "")[:20]}"'
        else:
            style = f', label="{f["id"]}\\n[{f["maturity"][0].upper()}] {f.get("content", "")[:20]}"'
        lines.append(f'  "{f["id"]}" [{style.lstrip(", ")}];')
    for t in board["threads"]:
        edge_style = ""
        if t["type"] == "contradicts":
            edge_style = ' [color=red, style=dashed]'
        elif t["type"] == "eliminates":
            edge_style = ' [color=red]'
        elif t["type"] == "supports":
            edge_style = ' [color=green]'
        lines.append(f'  "{t["from_id"]}" -> "{t["to_id"]}"{edge_style};')
    lines.append('}')
    return '\n'.join(lines)


def load_board(path: str) -> dict:
    return json.loads(Path(path).read_text())


def save_board(board: dict, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(board, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    case_file = sys.argv[2]

    if cmd == "init":
        title = sys.argv[3] if len(sys.argv) > 3 else "Untitled Case"
        desc = sys.argv[4] if len(sys.argv) > 4 else ""
        board = init_case(title, desc)
        save_board(board, case_file)
        print(json.dumps({"status": "created", "case_id": board["id"]}, indent=2))

    elif cmd == "add-fragment":
        board = load_board(case_file)
        frag = json.loads(sys.argv[3])
        result = add_fragment(board, frag)
        save_board(board, case_file)
        print(json.dumps(result, indent=2))

    elif cmd == "add-thread":
        board = load_board(case_file)
        thread = json.loads(sys.argv[3])
        result = add_thread(board, thread)
        save_board(board, case_file)
        print(json.dumps(result, indent=2))

    elif cmd == "evolve":
        board = load_board(case_file)
        fid = sys.argv[3]
        new_m = sys.argv[4]
        ok = evolve_fragment(board, fid, new_m)
        save_board(board, case_file)
        print(json.dumps({"evolved": ok}))

    elif cmd == "eliminate":
        board = load_board(case_file)
        fid = sys.argv[3]
        reason = sys.argv[4] if len(sys.argv) > 4 else "no reason given"
        ok = eliminate_fragment(board, fid, reason)
        save_board(board, case_file)
        print(json.dumps({"eliminated": ok}))

    elif cmd == "status":
        board = load_board(case_file)
        print(json.dumps(board_summary(board), indent=2))

    elif cmd == "export-graph":
        board = load_board(case_file)
        print(export_dot(board))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
