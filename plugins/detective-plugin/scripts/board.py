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
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from detective_mcp import legacy_board


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _usage(command: str | None = None) -> int:
    if command:
        return _error(f"Usage error: missing arguments for {command}")
    return _error("Usage: python board.py <command> <case_file> [args...]")


def _json_out(value: object, *, indent: int | None = 2) -> None:
    print(json.dumps(value, indent=indent, ensure_ascii=False))


def _parse_json(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        return _usage()

    cmd = argv[1]
    case_file = argv[2]

    try:
        if cmd == "init":
            title = argv[3] if len(argv) > 3 else "Untitled Case"
            desc = argv[4] if len(argv) > 4 else ""
            board = legacy_board.init_case(title, desc)
            legacy_board.save_board(board, case_file)
            _json_out({"status": "created", "case_id": board["id"]})
            return 0

        if cmd == "add-fragment":
            if len(argv) < 4:
                return _usage(cmd)
            board = legacy_board.load_board(case_file)
            fragment = _parse_json(argv[3])
            if not isinstance(fragment, dict):
                raise ValueError("Fragment JSON must be an object")
            result = legacy_board.add_fragment(board, fragment)
            legacy_board.save_board(board, case_file)
            _json_out(result)
            return 0

        if cmd == "add-thread":
            if len(argv) < 4:
                return _usage(cmd)
            board = legacy_board.load_board(case_file)
            thread = _parse_json(argv[3])
            if not isinstance(thread, dict):
                raise ValueError("Thread JSON must be an object")
            result = legacy_board.add_thread(board, thread)
            legacy_board.save_board(board, case_file)
            _json_out(result)
            return 0

        if cmd == "evolve":
            if len(argv) < 5:
                return _usage(cmd)
            board = legacy_board.load_board(case_file)
            fragment_id = argv[3]
            new_maturity = argv[4]
            ok = legacy_board.evolve_fragment(board, fragment_id, new_maturity)
            legacy_board.save_board(board, case_file)
            _json_out({"evolved": ok}, indent=None)
            return 0

        if cmd == "eliminate":
            if len(argv) < 4:
                return _usage(cmd)
            board = legacy_board.load_board(case_file)
            fragment_id = argv[3]
            reason = argv[4] if len(argv) > 4 else "no reason given"
            ok = legacy_board.eliminate_fragment(board, fragment_id, reason)
            legacy_board.save_board(board, case_file)
            _json_out({"eliminated": ok}, indent=None)
            return 0

        if cmd == "status":
            board = legacy_board.load_board(case_file)
            _json_out(legacy_board.board_summary(board))
            return 0

        if cmd == "export-graph":
            board = legacy_board.load_board(case_file)
            print(legacy_board.export_dot(board))
            return 0

        return _error(f"Unknown command: {cmd}")
    except FileNotFoundError:
        return _error(f"Case file not found: {case_file}")
    except (ValueError, KeyError) as exc:
        return _error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
