#!/usr/bin/env python3
"""Convergence detection — determines if a case can be closed.

Usage: python convergence.py <case_file>

Outputs a JSON report with:
  - converged: bool
  - conditions: dict of individual convergence checks
  - reasoning: str explanation

Convergence criteria:
  1. A confirmed hypothesis exists (confidence > upper threshold)
  2. All other hypotheses eliminated or below lower threshold
  3. Evidence chain from crime scene to conclusion has no gaps
  4. No unresolved 'requires' threads
"""

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from detective_mcp import legacy_convergence


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return _error("Usage: python convergence.py <case_file>")

    try:
        case_file = argv[1]
        board = legacy_convergence.load_board(case_file)
        result = legacy_convergence.check_convergence(board)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except FileNotFoundError:
        return _error(f"Case file not found: {case_file}")
    except json.JSONDecodeError as exc:
        return _error(f"Invalid JSON: {exc.msg}")
    except KeyError as exc:
        return _error(f"Missing required field: {exc.args[0]}")
    except ValueError as exc:
        return _error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
