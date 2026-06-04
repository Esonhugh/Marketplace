import json
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name, *args, check=True):
    return subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / script_name), *args],
        cwd=PLUGIN_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def test_board_script_delegates_to_legacy_board_utils(tmp_path):
    case_file = tmp_path / "case.json"

    created = run_script("board.py", "init", str(case_file), "Legacy Case", "Description")
    assert json.loads(created.stdout)["status"] == "created"

    fragment = json.dumps({"content": "Config drift", "role": "hypothesis", "maturity": "clue"})
    added = run_script("board.py", "add-fragment", str(case_file), fragment)
    fragment_id = json.loads(added.stdout)["id"]

    status = json.loads(run_script("board.py", "status", str(case_file)).stdout)
    assert status["title"] == "Legacy Case"
    assert status["active_hypotheses"] == 1

    evolved = json.loads(run_script("board.py", "evolve", str(case_file), fragment_id, "evidence").stdout)
    assert evolved == {"evolved": True}

    graph = run_script("board.py", "export-graph", str(case_file)).stdout
    assert graph.startswith("digraph CaseBoard")
    assert fragment_id in graph


def test_scoring_script_delegates_to_legacy_scoring_utils(tmp_path):
    case_file = tmp_path / "score.json"
    board = {
        "id": "legacy-score",
        "title": "Score",
        "phase": "opening",
        "fragments": [
            {"id": "h1", "role": "hypothesis", "maturity": "clue", "confidence": 0.5},
            {"id": "c1", "role": "constraint", "maturity": "evidence", "confidence": 1.0},
        ],
        "threads": [{"from_id": "c1", "to_id": "h1", "type": "contradicts"}],
        "actions_history": [],
        "config": {"confidence_threshold_eliminate": 0.15},
    }
    case_file.write_text(json.dumps(board), encoding="utf-8")

    phase = json.loads(run_script("scoring.py", "suggest-phase", str(case_file)).stdout)
    assert phase["suggested_phase"] in {"opening", "pursuit"}

    candidates = json.dumps([
        {"description": "Check h1", "target_hypotheses": ["h1"], "feasibility": 0.8, "cost": 2}
    ])
    scored = json.loads(run_script("scoring.py", "score-actions", str(case_file), candidates).stdout)
    assert scored[0]["description"] == "Check h1"
    assert scored[0]["score"] > 0

    changes = json.loads(run_script("scoring.py", "propagate", str(case_file)).stdout)
    assert changes["weakened"] == [{"id": "h1", "new_confidence": 0.35}]


def test_convergence_script_delegates_to_legacy_convergence_utils(tmp_path):
    case_file = tmp_path / "converged.json"
    board = {
        "id": "legacy-converged",
        "title": "Converged",
        "fragments": [
            {"id": "h1", "role": "hypothesis", "maturity": "evidence", "confidence": 0.9},
            {"id": "h2", "role": "hypothesis", "maturity": "clue", "confidence": 0.1, "status": "eliminated"},
        ],
        "threads": [],
        "config": {"confidence_threshold_confirm": 0.85, "confidence_threshold_eliminate": 0.15},
    }
    case_file.write_text(json.dumps(board), encoding="utf-8")

    result = json.loads(run_script("convergence.py", str(case_file)).stdout)
    assert result["converged"] is True
    assert result["recommendation"] == "close-case"


def test_board_script_prints_unicode_json_without_ascii_escapes(tmp_path):
    case_file = tmp_path / "unicode.json"
    run_script("board.py", "init", str(case_file), "Unicode Case", "Description")

    fragment = json.dumps({"content": "线索", "role": "hypothesis", "maturity": "clue"})
    added = run_script("board.py", "add-fragment", str(case_file), fragment)

    assert "线索" in added.stdout
    assert "\\u7ebf\\u7d22" not in added.stdout


def test_board_script_reports_missing_args_without_traceback(tmp_path):
    case_file = tmp_path / "missing.json"
    run_script("board.py", "init", str(case_file), "Missing Args", "Description")

    result = run_script("board.py", "add-fragment", str(case_file), check=False)

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_board_script_reports_missing_case_file_without_traceback(tmp_path):
    missing_case = tmp_path / "does-not-exist.json"

    result = run_script("board.py", "status", str(missing_case), check=False)

    assert result.returncode != 0
    assert "Case file not found" in result.stderr
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_board_script_reports_invalid_json_without_traceback(tmp_path):
    case_file = tmp_path / "invalid-json.json"
    run_script("board.py", "init", str(case_file), "Invalid JSON", "Description")

    result = run_script("board.py", "add-fragment", str(case_file), "{not-json", check=False)

    assert result.returncode != 0
    assert "invalid json" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_board_script_reports_domain_errors_without_traceback(tmp_path):
    case_file = tmp_path / "domain-error.json"
    run_script("board.py", "init", str(case_file), "Domain Error", "Description")

    result = run_script("board.py", "add-thread", str(case_file), json.dumps({"type": "supports"}), check=False)

    assert result.returncode != 0
    assert "thread requires fields" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_scoring_script_prints_unicode_json_without_ascii_escapes(tmp_path):
    case_file = tmp_path / "scoring-unicode.json"
    board = {
        "fragments": [{"id": "h1", "role": "hypothesis", "maturity": "clue", "confidence": 0.5}],
        "threads": [],
    }
    case_file.write_text(json.dumps(board), encoding="utf-8")

    candidates = json.dumps([{"description": "检查线索", "target_hypotheses": ["h1"], "feasibility": 0.8, "cost": 2}])
    scored = run_script("scoring.py", "score-actions", str(case_file), candidates)

    assert "检查线索" in scored.stdout
    assert "\\u68c0\\u67e5\\u7ebf\\u7d22" not in scored.stdout


def test_scoring_script_reports_missing_args_without_traceback(tmp_path):
    case_file = tmp_path / "scoring-missing.json"
    case_file.write_text(json.dumps({"fragments": [], "threads": []}), encoding="utf-8")

    result = run_script("scoring.py", "score-actions", str(case_file), check=False)

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_scoring_script_reports_missing_case_file_without_traceback(tmp_path):
    missing_case = tmp_path / "does-not-exist.json"

    result = run_script("scoring.py", "suggest-phase", str(missing_case), check=False)

    assert result.returncode != 0
    assert "Case file not found" in result.stderr
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_scoring_script_reports_invalid_json_without_traceback(tmp_path):
    case_file = tmp_path / "scoring-invalid-json.json"
    case_file.write_text(json.dumps({"fragments": [], "threads": []}), encoding="utf-8")

    result = run_script("scoring.py", "score-actions", str(case_file), "{not-json", check=False)

    assert result.returncode != 0
    assert "invalid json" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_convergence_script_prints_unicode_json_without_ascii_escapes(tmp_path):
    case_file = tmp_path / "convergence-unicode.json"
    board = {
        "id": "unicode-convergence",
        "title": "收敛",
        "fragments": [
            {"id": "线索", "role": "hypothesis", "maturity": "evidence", "confidence": 0.9},
        ],
        "threads": [],
        "config": {"confidence_threshold_confirm": 0.85, "confidence_threshold_eliminate": 0.15},
    }
    case_file.write_text(json.dumps(board), encoding="utf-8")

    result = run_script("convergence.py", str(case_file))

    assert "线索" in result.stdout
    assert "\\u7ebf\\u7d22" not in result.stdout


def test_convergence_script_reports_missing_args_without_traceback():
    result = run_script("convergence.py", check=False)

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_convergence_script_reports_missing_case_file_without_traceback(tmp_path):
    missing_case = tmp_path / "does-not-exist.json"

    result = run_script("convergence.py", str(missing_case), check=False)

    assert result.returncode != 0
    assert "Case file not found" in result.stderr
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_convergence_script_reports_invalid_json_without_traceback(tmp_path):
    case_file = tmp_path / "invalid-convergence.json"
    case_file.write_text("{not-json", encoding="utf-8")

    result = run_script("convergence.py", str(case_file), check=False)

    assert result.returncode != 0
    assert "invalid json" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_convergence_script_reports_bad_case_shape_without_traceback(tmp_path):
    case_file = tmp_path / "bad-convergence.json"
    case_file.write_text(json.dumps({"fragments": []}), encoding="utf-8")

    result = run_script("convergence.py", str(case_file), check=False)

    assert result.returncode != 0
    assert "missing required field" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert result.stdout == ""


def test_legacy_utilities_reuse_board_io_and_describe_conclusion_chain_as_informational():
    from detective_mcp import legacy_board, legacy_convergence, legacy_scoring

    assert legacy_scoring.load_board is legacy_board.load_board
    assert legacy_scoring.save_board is legacy_board.save_board
    assert legacy_convergence.load_board is legacy_board.load_board
    assert "informational" in (legacy_convergence.__doc__ or "").lower()


def test_legacy_scoring_reuses_board_io_and_elimination_metadata(tmp_path):
    from detective_mcp import legacy_scoring

    case_file = tmp_path / "nested" / "scoring-save.json"
    board = {
        "id": "legacy-scoring-reuse",
        "title": "Scoring Reuse",
        "phase": "opening",
        "fragments": [
            {"id": "h1", "role": "hypothesis", "maturity": "clue", "confidence": 0.5},
            {"id": "c1", "role": "constraint", "maturity": "evidence", "confidence": 1.0},
        ],
        "threads": [{"from_id": "c1", "to_id": "h1", "type": "eliminates"}],
        "actions_history": [],
        "config": {"confidence_threshold_eliminate": 0.15},
    }

    legacy_scoring.save_board(board, case_file)
    loaded = legacy_scoring.load_board(case_file)
    changes = legacy_scoring.propagate_constraints(loaded)

    hypothesis = loaded["fragments"][0]
    assert changes == {"eliminated": ["h1"], "weakened": []}
    assert hypothesis["status"] == "eliminated"
    assert hypothesis["elimination_reason"] == "Eliminated by constraint c1"
    assert "eliminated_at" in hypothesis
    assert "updated_at" in loaded


def test_legacy_script_wrappers_remain_thin():
    board_source = (PLUGIN_ROOT / "scripts" / "board.py").read_text(encoding="utf-8")
    assert "def init_case" not in board_source
    assert "def add_fragment" not in board_source
    assert "def board_summary" not in board_source

    scoring_source = (PLUGIN_ROOT / "scripts" / "scoring.py").read_text(encoding="utf-8")
    assert "def propagate_constraints" not in scoring_source
    assert "def score_candidate_actions" not in scoring_source
    assert "def suggest_phase" not in scoring_source

    convergence_source = (PLUGIN_ROOT / "scripts" / "convergence.py").read_text(encoding="utf-8")
    assert "def check_convergence" not in convergence_source
