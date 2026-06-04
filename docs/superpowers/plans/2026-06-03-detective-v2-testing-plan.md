# Detective v2 and v2.1 Testing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify Detective v2 MCP Graph Core and v2.1 Autonomous Investigation with deterministic unit tests, MCP wrapper smoke tests, export tests, documentation checks, and manual Claude Code MCP validation.

**Architecture:** Use pytest for pure Python modules and server wrapper functions, temporary directories for `.detective/` persistence, grep/json checks for plugin configuration and documentation, and manual `/mcp` validation for Claude Code integration. Tests must never write to the repository root `.detective/` during automated runs.

**Tech Stack:** Python 3.11+, uv, pytest, stdlib `json`, `pathlib`, temporary directories, Claude Code `/mcp` manual validation.

---

## Test Matrix

| Area | Test File / Check | Purpose |
|------|-------------------|---------|
| uv and MCP config | `tests/test_config.py` | Verify `pyproject.toml`, `.mcp.json`, package import |
| Persistence | `tests/test_store.py` | Verify case creation, load/save, events, node/edge mutation |
| Graph algorithms | `tests/test_graph.py` | Verify overview, list/search, neighbors, shortest path |
| Legacy scripts | `tests/test_legacy_scripts.py` | Verify scripts are thin CLI wrappers over detective_mcp utilities |
| Exports | `tests/test_exports.py` | Verify Markdown/Mermaid projections and v2.1 enhanced artifacts |
| MCP wrappers | `tests/test_server_tools.py` | Verify tool functions call underlying modules correctly |
| Scheduler | `tests/test_scheduler.py` | Verify direction memory, action queue, scoring, user guidance |
| Signals | `tests/test_signals.py` | Verify convergence and deadlock recommendations |
| Docs/config | grep/json commands | Verify README/plugin metadata and `.mcp.json` syntax |
| Manual Claude Code | `/mcp` | Verify MCP server/tool discovery in actual Claude Code |

## Task 1: v2 configuration tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_config.py`
- Verify: `plugins/detective-plugin/pyproject.toml`
- Verify: `plugins/detective-plugin/.mcp.json`

- [ ] **Step 1: Run config tests**

Run from `plugins/detective-plugin`:

```bash
uv run pytest tests/test_config.py -v
```

Expected: PASS with tests:

```text
test_pyproject_declares_mcp_dependency PASSED
test_mcp_json_uses_uv_and_plugin_root PASSED
test_package_imports PASSED
```

- [ ] **Step 2: Validate `.mcp.json` syntax**

Run:

```bash
python -m json.tool .mcp.json >/tmp/detective-mcp-json-check.json
```

Expected: exit code 0.

- [ ] **Step 3: Verify uv lock is consistent**

Run:

```bash
uv lock --check
```

Expected: exit code 0. If this uv version does not support `--check`, run `uv lock` and verify `git diff -- uv.lock` is empty or intentional.

## Task 2: v2 persistence and schema tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_store.py`
- Verify: `plugins/detective-plugin/detective_mcp/models.py`
- Verify: `plugins/detective-plugin/detective_mcp/store.py`

- [ ] **Step 1: Run persistence tests**

Run:

```bash
uv run pytest tests/test_store.py -v
```

Expected: PASS with coverage for:

- case directory creation
- generated slug IDs
- case loading
- missing case error
- event log append
- node add/update persistence
- edge add persistence
- missing edge endpoint rejection
- invalid node/edge type rejection

- [ ] **Step 2: Verify no real project `.detective/` was created by tests**

Run from repository root:

```bash
test ! -d .detective
```

Expected: exit code 0. If `.detective/` exists because of manual testing, inspect before deleting; do not remove user data without explicit approval.

- [ ] **Step 3: Inspect an isolated temp case manually**

Run from `plugins/detective-plugin`:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from detective_mcp import store

with TemporaryDirectory() as tmp:
    result = store.open_case(Path(tmp), 'Manual Persistence Check', 'Temporary test', case_id='manual-check')
    node = store.add_node(Path(tmp), 'manual-check', 'observation', 'Temporary observation')
    print(result['case_id'])
    print(node['type'])
    print((Path(tmp) / '.detective' / 'cases' / 'manual-check' / 'case.json').exists())
PY
```

Expected output:

```text
manual-check
observation
True
```

## Task 3: v2 graph query tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_graph.py`
- Verify: `plugins/detective-plugin/detective_mcp/graph.py`

- [ ] **Step 1: Run graph tests**

Run from `plugins/detective-plugin`:

```bash
uv run pytest tests/test_graph.py -v
```

Expected: PASS with coverage for:

- graph overview counts
- graph density
- list nodes by type/status/tag
- search by content and tags
- incoming/outgoing neighbors
- directed shortest path
- undirected shortest path
- no-path behavior

- [ ] **Step 2: Manual graph smoke test**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from detective_mcp import graph, store

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    store.open_case(root, 'Path Check', 'Temporary graph', case_id='path-check')
    a = store.add_node(root, 'path-check', 'observation', 'A')
    b = store.add_node(root, 'path-check', 'evidence', 'B')
    c = store.add_node(root, 'path-check', 'hypothesis', 'C')
    store.add_edge(root, 'path-check', a['id'], b['id'], 'derives')
    store.add_edge(root, 'path-check', b['id'], c['id'], 'supports')
    print(graph.graph_overview(root, 'path-check')['total_nodes'])
    print([n['content'] for n in graph.shortest_path(root, 'path-check', a['id'], c['id'])['nodes']])
PY
```

Expected output:

```text
3
['A', 'B', 'C']
```

## Task 4: legacy script wrapper tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_legacy_scripts.py`
- Verify: `plugins/detective-plugin/scripts/board.py`
- Verify: `plugins/detective-plugin/scripts/scoring.py`
- Verify: `plugins/detective-plugin/scripts/convergence.py`
- Verify: `plugins/detective-plugin/detective_mcp/legacy_board.py`
- Verify: `plugins/detective-plugin/detective_mcp/legacy_scoring.py`
- Verify: `plugins/detective-plugin/detective_mcp/legacy_convergence.py`

- [ ] **Step 1: Run legacy script tests**

Run from `plugins/detective-plugin`:

```bash
uv run pytest tests/test_legacy_scripts.py -v
```

Expected: PASS. The tests should exercise `scripts/board.py`, `scripts/scoring.py`, and `scripts/convergence.py` through subprocess calls and verify they delegate to package utilities.

- [ ] **Step 2: Verify wrappers contain no duplicated business logic markers**

Run:

```bash
grep -R "def propagate_constraints\|def check_convergence\|def init_case" -n scripts || true
```

Expected: no output. Those functions should live under `detective_mcp/legacy_*.py`, not under `scripts/`.

- [ ] **Step 3: Run v2 regression tests with legacy scripts**

Run:

```bash
uv run pytest tests/test_config.py tests/test_store.py tests/test_graph.py tests/test_legacy_scripts.py -v
```

Expected: all tests PASS.

## Task 5: v2 export tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_exports.py`
- Verify: `plugins/detective-plugin/detective_mcp/exports.py`

- [ ] **Step 1: Run export tests**

Run:

```bash
uv run pytest tests/test_exports.py -v
```

Expected: PASS for Markdown and Mermaid export tests.

- [ ] **Step 2: Manual Markdown/Mermaid smoke test**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from detective_mcp import exports, store

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    store.open_case(root, 'Export Smoke', 'Temporary export', case_id='export-smoke')
    node = store.add_node(root, 'export-smoke', 'evidence', 'Evidence text')
    markdown = exports.export_markdown(root, 'export-smoke')
    mermaid = exports.export_mermaid(root, 'export-smoke')
    print(Path(markdown['path']).name)
    print(Path(mermaid['path']).name)
    print('Evidence text' in Path(markdown['path']).read_text())
    print(Path(mermaid['path']).read_text().startswith('graph LR'))
PY
```

Expected output:

```text
notes.md
graph.mmd
True
True
```

## Task 5: v2 MCP wrapper tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_server_tools.py`
- Verify: `plugins/detective-plugin/detective_mcp/server.py`

- [ ] **Step 1: Run MCP wrapper tests**

Run:

```bash
uv run pytest tests/test_server_tools.py -v
```

Expected: PASS for case creation, node/edge mutation, overview, shortest path, and export wrapper tests.

- [ ] **Step 2: Run server import smoke test**

Run:

```bash
uv run python -c "from detective_mcp.server import mcp; print(mcp.name)"
```

Expected output contains:

```text
detective
```

- [ ] **Step 3: Run module startup smoke test**

Run:

```bash
uv run python -m detective_mcp.server
```

Expected: process starts and waits for MCP stdio input without immediate traceback. Stop with Ctrl-C after confirming it starts.

## Task 6: v2.1 scheduler tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_scheduler.py`
- Verify: `plugins/detective-plugin/detective_mcp/scheduler.py`

- [ ] **Step 1: Run scheduler tests**

Run:

```bash
uv run pytest tests/test_scheduler.py -v
```

Expected: PASS with coverage for:

- new case scheduler defaults
- attempted direction tracking
- cold direction marking after three no-evidence attempts
- next action priority sorting
- candidate scoring
- cold direction penalty
- user guidance capture as high-priority graph state

- [ ] **Step 2: Manual scheduler smoke test**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from detective_mcp import scheduler, store

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    store.open_case(root, 'Scheduler Smoke', 'Temporary scheduler', case_id='sched-smoke')
    h = store.add_node(root, 'sched-smoke', 'hypothesis', 'Candidate')
    for _ in range(3):
        direction = scheduler.record_direction_attempt(root, 'sched-smoke', 'Check candidate', [h['id']], 0)
    action = scheduler.add_next_action(root, 'sched-smoke', 'Try other route', 'evidence-hunter', 0.8, 'Avoid cold direction')
    print(direction['status'])
    print(action['status'])
PY
```

Expected output:

```text
cold
pending
```

## Task 7: v2.1 signal tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_signals.py`
- Verify: `plugins/detective-plugin/detective_mcp/signals.py`

- [ ] **Step 1: Run signal tests**

Run:

```bash
uv run pytest tests/test_signals.py -v
```

Expected: PASS with coverage for:

- convergence false with blocking open question
- convergence true with supported confirmed hypothesis and rejected alternative
- deadlock true when all candidate actions score low and no graph changes occurred
- deadlock false when at least one useful action remains

- [ ] **Step 2: Manual signal smoke test**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from detective_mcp import signals, store

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    store.open_case(root, 'Signal Smoke', 'Temporary signals', case_id='signal-smoke')
    e = store.add_node(root, 'signal-smoke', 'evidence', 'Strong evidence')
    h = store.add_node(root, 'signal-smoke', 'hypothesis', 'Supported answer', confidence=0.9)
    store.add_edge(root, 'signal-smoke', e['id'], h['id'], 'supports')
    print(signals.convergence_status(root, 'signal-smoke')['recommendation'])
PY
```

Expected output:

```text
close-case
```

## Task 8: v2.1 enhanced export tests

**Files:**
- Test: `plugins/detective-plugin/tests/test_exports.py`
- Verify: `plugins/detective-plugin/detective_mcp/exports.py`

- [ ] **Step 1: Run enhanced export tests**

Run:

```bash
uv run pytest tests/test_exports.py -v
```

Expected: PASS including scheduler and focused Mermaid tests.

- [ ] **Step 2: Verify Markdown includes scheduler details**

Run a manual temp export:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from detective_mcp import exports, scheduler, store

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    store.open_case(root, 'Enhanced Export', 'Temporary export', case_id='enhanced-export')
    for _ in range(3):
        scheduler.record_direction_attempt(root, 'enhanced-export', 'Cold path', [], 0)
    result = exports.export_markdown(root, 'enhanced-export')
    text = Path(result['path']).read_text()
    print('## Scheduler' in text)
    print('Cold path' in text)
    print('cold' in text)
PY
```

Expected output:

```text
True
True
True
```

## Task 9: Full automated test suite

**Files:**
- All test files under `plugins/detective-plugin/tests/`

- [ ] **Step 1: Run all pytest tests**

Run from `plugins/detective-plugin`:

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run tests twice to catch hidden state coupling**

Run:

```bash
uv run pytest -v && uv run pytest -v
```

Expected: both runs PASS. Failures on the second run usually indicate tests wrote shared state outside `tmp_path`.

- [ ] **Step 3: Verify generated temp files did not dirty repo**

Run from repository root:

```bash
git status --short
```

Expected: only intentional source/docs/test files are modified. No root `.detective/` should appear from automated tests.

## Task 10: Documentation and plugin metadata checks

**Files:**
- Verify: `plugins/detective-plugin/README.md`
- Verify: `plugins/detective-plugin/README-zh.md`
- Verify: `plugins/detective-plugin/.claude-plugin/plugin.json`
- Verify: `plugins/detective-plugin/agents/*.md`
- Verify: `plugins/detective-plugin/skills/*/SKILL.md`

- [ ] **Step 1: Verify v2 documentation references**

Run from `plugins/detective-plugin`:

```bash
grep -R "detective_open_case\|detective_shortest_path\|v2 MCP" -n README.md README-zh.md .claude-plugin/plugin.json
```

Expected: output includes README and plugin metadata references.

- [ ] **Step 2: Verify v2.1 documentation references**

Run:

```bash
grep -R "v2.1\|Autonomous Investigation\|自治调查" -n README.md README-zh.md .claude-plugin/plugin.json
```

Expected: output includes README and plugin metadata references.

- [ ] **Step 3: Verify specialist agent files exist**

Run:

```bash
ls agents/lead-investigator.md agents/hypothesis-generator.md agents/evidence-hunter.md agents/contradiction-finder.md agents/path-analyzer.md agents/report-writer.md
```

Expected: all six paths print.

- [ ] **Step 4: Verify MCP-first skill references**

Run:

```bash
grep -R "detective_graph_overview\|detective_apply_user_guidance\|detective_convergence_status" -n skills
```

Expected: output includes `investigate`, `review-board`, `discuss-case`, and `close-case` skill files.

- [ ] **Step 5: Verify direct JSON editing is not recommended**

Run:

```bash
grep -R "edit.*case.json\|directly edit.*\.detective" -n agents skills README.md README-zh.md || true
```

Expected: no output that tells agents to directly edit `case.json`. Statements that direct editing is disallowed are acceptable.

## Task 11: Manual Claude Code MCP validation

**Files:**
- Verify actual plugin runtime behavior.

- [ ] **Step 1: Reload Claude Code plugin environment**

Restart Claude Code or start a fresh session with the plugin available.

Expected: plugin loads without MCP startup errors.

- [ ] **Step 2: Check MCP server discovery**

Run in Claude Code:

```text
/mcp
```

Expected: a plugin-provided `detective` server appears.

- [ ] **Step 3: Check v2 tool discovery**

In the `/mcp` output or tool list, verify tools equivalent to:

```text
detective_open_case
detective_add_node
detective_add_edge
detective_graph_overview
detective_search_nodes
detective_neighbors
detective_shortest_path
detective_export_markdown
detective_export_mermaid
```

Expected: all are discoverable.

- [ ] **Step 4: Check v2.1 tool discovery**

Verify tools equivalent to:

```text
detective_record_direction_attempt
detective_add_next_action
detective_score_candidate_actions
detective_apply_user_guidance
detective_convergence_status
detective_deadlock_status
```

Expected: all are discoverable.

- [ ] **Step 5: Manual end-to-end case smoke test**

Using Claude Code MCP tools, perform this flow in a scratch project or temporary directory:

```text
1. detective_open_case(title="MCP smoke test", description="Validate Detective MCP")
2. detective_add_node(type="observation", content="Observed behavior")
3. detective_add_node(type="hypothesis", content="Possible explanation")
4. detective_add_edge(type="supports", from_id=<observation>, to_id=<hypothesis>)
5. detective_graph_overview(case_id=<case>)
6. detective_shortest_path(case_id=<case>, from_id=<observation>, to_id=<hypothesis>)
7. detective_export_markdown(case_id=<case>)
8. detective_export_mermaid(case_id=<case>)
```

Expected:

- overview reports 2 nodes and 1 edge
- shortest path returns observation → hypothesis
- `notes.md` and `graph.mmd` are created under `.detective/cases/<case-id>/`

## Task 12: Final release validation

**Files:**
- Entire Detective plugin.

- [ ] **Step 1: Run all automated checks**

Run from `plugins/detective-plugin`:

```bash
uv run pytest -v
python -m json.tool .mcp.json >/tmp/detective-mcp-json-check.json
```

Expected: tests PASS and JSON validation exits 0.

- [ ] **Step 2: Review git diff**

Run from repository root:

```bash
git diff -- plugins/detective-plugin docs/superpowers/specs docs/superpowers/plans
```

Expected: diff contains only intended Detective v2/v2.1 code, tests, docs, specs, and plans.

- [ ] **Step 3: Confirm no accidental generated case data is staged**

Run:

```bash
git status --short
```

Expected: no `.detective/` generated case files appear unless the user explicitly asked to keep them.

- [ ] **Step 4: Verify acceptance criteria**

Confirm manually:

- v2 MCP server is registered through `.mcp.json` and uv.
- v2 tools can create and query graph state.
- JSON persists under `.detective/cases/<case-id>/case.json`.
- Markdown and Mermaid are generated projections.
- v2.1 scheduler memory records directions and next actions.
- v2.1 user guidance is captured as graph state.
- v2.1 convergence/deadlock helpers return conservative recommendations.
- agents and skills instruct MCP-first state mutation.

- [ ] **Step 5: Commit if commits are authorized**

If the user authorized commits:

```bash
git add plugins/detective-plugin docs/superpowers/specs docs/superpowers/plans
git commit -m "feat: add detective MCP graph and autonomous investigation plans"
```
