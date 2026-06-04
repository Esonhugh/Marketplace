#!/usr/bin/env python3
"""Strategy scoring and constraint propagation engine.

Usage: python scoring.py <command> <case_file> [args...]

Commands:
  propagate <case_file>                 Run constraint propagation
  score-actions <case_file> <json>      Score candidate actions
  suggest-phase <case_file>             Suggest current investigation phase
"""

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from detective_mcp import legacy_scoring


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _usage(command: str | None = None) -> int:
    if command:
        return _error(f"Usage error: missing arguments for {command}")
    return _error("Usage: python scoring.py <command> <case_file> [args...]")


def _json_out(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


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
        if cmd == "propagate":
            board = legacy_scoring.load_board(case_file)
            changes = legacy_scoring.propagate_constraints(board)
            legacy_scoring.save_board(board, case_file)
            _json_out(changes)
            return 0

        if cmd == "score-actions":
            if len(argv) < 4:
                return _usage(cmd)
            board = legacy_scoring.load_board(case_file)
            candidates = _parse_json(argv[3])
            if not isinstance(candidates, list):
                raise ValueError("Candidates JSON must be an array")
            scored = legacy_scoring.score_candidate_actions(board, candidates)
            _json_out(scored)
            return 0

        if cmd == "suggest-phase":
            board = legacy_scoring.load_board(case_file)
            result = legacy_scoring.suggest_phase(board)
            _json_out(result)
            return 0

        return _error(f"Unknown command: {cmd}")
    except FileNotFoundError:
        return _error(f"Case file not found: {case_file}")
    except (ValueError, KeyError) as exc:
        return _error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
