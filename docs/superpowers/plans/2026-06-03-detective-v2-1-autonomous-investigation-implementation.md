# Detective v2.1 Autonomous Investigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add case-local scheduling memory, deterministic convergence/deadlock helpers, richer exports, specialist agents, and MCP-first skill guidance on top of the Detective v2 graph core.

**Architecture:** Keep the MCP server as the only state mutation interface and add deterministic v2.1 helpers as pure Python modules behind new MCP tools. Claude skills and agents orchestrate reasoning and dispatch; the MCP server records scheduler state, computes candidate-action scores, detects deadlocks/convergence, applies user guidance as graph state, and generates richer artifacts.

**Tech Stack:** Python 3.11+, uv, `mcp` Python SDK with FastMCP, pytest, Claude Code plugin agents/skills Markdown.

---

## Scope Check

This plan depends on Detective v2 MCP Graph Core being implemented first. It does not add external OSINT/code/RCA integrations and does not make the MCP server call Claude. It adds deterministic orchestration support and plugin instructions for Claude/subagents to use those tools.

## File Structure

Create or modify these files:

- Create: `plugins/detective-plugin/detective_mcp/scheduler.py` — scheduler state, candidate action scoring, cold direction tracking.
- Create: `plugins/detective-plugin/detective_mcp/signals.py` — convergence and deadlock detection.
- Create: `plugins/detective-plugin/tests/test_scheduler.py` — scheduler unit tests.
- Create: `plugins/detective-plugin/tests/test_signals.py` — convergence/deadlock tests.
- Modify: `plugins/detective-plugin/detective_mcp/models.py` — add default scheduler and signal config fields.
- Modify: `plugins/detective-plugin/detective_mcp/store.py` — support action/event fields needed by scheduler.
- Modify: `plugins/detective-plugin/detective_mcp/exports.py` — richer Markdown and focused Mermaid exports.
- Modify: `plugins/detective-plugin/detective_mcp/server.py` — expose v2.1 MCP tools.
- Create: `plugins/detective-plugin/agents/lead-investigator.md` — orchestrator agent instructions.
- Create: `plugins/detective-plugin/agents/hypothesis-generator.md` — hypothesis specialist.
- Create: `plugins/detective-plugin/agents/evidence-hunter.md` — evidence specialist.
- Create: `plugins/detective-plugin/agents/contradiction-finder.md` — falsification specialist.
- Create: `plugins/detective-plugin/agents/path-analyzer.md` — graph gap specialist.
- Create: `plugins/detective-plugin/agents/report-writer.md` — artifact specialist.
- Modify: `plugins/detective-plugin/skills/investigate/SKILL.md` — MCP-first lead loop.
- Modify: `plugins/detective-plugin/skills/review-board/SKILL.md` — MCP-first review/export.
- Modify: `plugins/detective-plugin/skills/discuss-case/SKILL.md` — user guidance writes through MCP.
- Modify: `plugins/detective-plugin/skills/close-case/SKILL.md` — use convergence signal and export resolution.
- Modify: `plugins/detective-plugin/README.md` — document v2.1 automation.
- Modify: `plugins/detective-plugin/README-zh.md` — document v2.1 automation in Chinese.

## Task 1: Add scheduler state to cases

**Files:**
- Modify: `plugins/detective-plugin/detective_mcp/models.py`
- Create: `plugins/detective-plugin/tests/test_scheduler.py`
- Create: `plugins/detective-plugin/detective_mcp/scheduler.py`

- [ ] **Step 1: Write failing scheduler default test**

Create `plugins/detective-plugin/tests/test_scheduler.py`:

```python
from detective_mcp import scheduler, store


def test_new_case_has_scheduler_state(tmp_path):
    store.open_case(tmp_path, "Scheduler Case", "Description", case_id="scheduler-case")

    case = store.load_case(tmp_path, "scheduler-case")

    assert case["scheduler"] == {
        "attempted_directions": [],
        "next_actions": [],
    }
    assert case["config"]["autonomy"] == "full_auto"
    assert case["config"]["user_override_policy"] == "always_priority"
    assert case["config"]["deadlock_score_threshold"] == 0.3
    assert case["config"]["confidence_threshold_confirm"] == 0.85
    assert case["config"]["confidence_threshold_eliminate"] == 0.15
```

- [ ] **Step 2: Run test to verify failure**

Run from `plugins/detective-plugin`:

```bash
uv run pytest tests/test_scheduler.py::test_new_case_has_scheduler_state -v
```

Expected: FAIL because `scheduler.py` is missing and/or cases do not include `scheduler`.

- [ ] **Step 3: Extend default case model**

Modify `plugins/detective-plugin/detective_mcp/models.py` so `DEFAULT_CONFIG` becomes:

```python
DEFAULT_CONFIG = {
    "autonomy": "full_auto",
    "checkpoint_interval": 5,
    "max_actions": 50,
    "user_override_policy": "always_priority",
    "deadlock_score_threshold": 0.3,
    "confidence_threshold_confirm": 0.85,
    "confidence_threshold_eliminate": 0.15,
}
```

Modify `make_case()` to include scheduler state:

```python
        "actions": [],
        "scheduler": {
            "attempted_directions": [],
            "next_actions": [],
        },
```

- [ ] **Step 4: Add scheduler module skeleton**

Create `plugins/detective-plugin/detective_mcp/scheduler.py`:

```python
from pathlib import Path
from typing import Any

from . import store


def ensure_scheduler(case: dict[str, Any]) -> dict[str, Any]:
    scheduler = case.setdefault("scheduler", {})
    scheduler.setdefault("attempted_directions", [])
    scheduler.setdefault("next_actions", [])
    return scheduler
```

- [ ] **Step 5: Run scheduler default test**

Run:

```bash
uv run pytest tests/test_scheduler.py::test_new_case_has_scheduler_state -v
```

Expected: PASS.

- [ ] **Step 6: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/models.py plugins/detective-plugin/detective_mcp/scheduler.py plugins/detective-plugin/tests/test_scheduler.py
git commit -m "feat: add detective scheduler state"
```

## Task 2: Implement attempted directions and next actions

**Files:**
- Modify: `plugins/detective-plugin/tests/test_scheduler.py`
- Modify: `plugins/detective-plugin/detective_mcp/scheduler.py`

- [ ] **Step 1: Add failing scheduler mutation tests**

Append to `plugins/detective-plugin/tests/test_scheduler.py`:

```python

def test_record_attempted_direction_marks_cold_after_three_empty_attempts(tmp_path):
    store.open_case(tmp_path, "Cold Case", "Description", case_id="cold-case")
    node = store.add_node(tmp_path, "cold-case", "hypothesis", "Maybe cache issue")

    first = scheduler.record_direction_attempt(
        tmp_path,
        "cold-case",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )
    second = scheduler.record_direction_attempt(
        tmp_path,
        "cold-case",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )
    third = scheduler.record_direction_attempt(
        tmp_path,
        "cold-case",
        description="Investigate cache issue",
        target_node_ids=[node["id"]],
        new_evidence_count=0,
    )

    assert first["attempts"] == 1
    assert second["attempts"] == 2
    assert third["attempts"] == 3
    assert third["status"] == "cold"


def test_add_next_action_sorts_by_priority(tmp_path):
    store.open_case(tmp_path, "Actions", "Description", case_id="actions")

    low = scheduler.add_next_action(tmp_path, "actions", "Low value", "evidence-hunter", 0.2, "cheap but narrow")
    high = scheduler.add_next_action(tmp_path, "actions", "High value", "contradiction-finder", 0.9, "tests leading theory")

    case = store.load_case(tmp_path, "actions")
    actions = case["scheduler"]["next_actions"]
    assert [action["id"] for action in actions] == [high["id"], low["id"]]
    assert actions[0]["status"] == "pending"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_scheduler.py -v
```

Expected: FAIL because mutation functions are missing.

- [ ] **Step 3: Implement scheduler mutations**

Modify `plugins/detective-plugin/detective_mcp/scheduler.py`:

```python
from pathlib import Path
from typing import Any

from . import store
from .ids import new_id, utc_now


def ensure_scheduler(case: dict[str, Any]) -> dict[str, Any]:
    scheduler = case.setdefault("scheduler", {})
    scheduler.setdefault("attempted_directions", [])
    scheduler.setdefault("next_actions", [])
    return scheduler


def _same_direction(direction: dict[str, Any], description: str, target_node_ids: list[str]) -> bool:
    return direction["description"] == description and sorted(direction["target_node_ids"]) == sorted(target_node_ids)


def record_direction_attempt(
    workspace: str | Path | None,
    case_id: str,
    description: str,
    target_node_ids: list[str],
    new_evidence_count: int,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    case_scheduler = ensure_scheduler(case)
    for direction in case_scheduler["attempted_directions"]:
        if _same_direction(direction, description, target_node_ids):
            direction["attempts"] += 1
            direction["new_evidence_count"] += new_evidence_count
            direction["last_attempted_at"] = utc_now()
            if direction["attempts"] >= 3 and direction["new_evidence_count"] == 0:
                direction["status"] = "cold"
            store.save_case(workspace, case, event={"type": "direction_attempted", "case_id": case_id, "direction_id": direction["id"]})
            return direction
    direction = {
        "id": new_id("dir"),
        "description": description,
        "target_node_ids": target_node_ids,
        "attempts": 1,
        "new_evidence_count": new_evidence_count,
        "status": "cold" if new_evidence_count == 0 and 1 >= 3 else "active",
        "last_attempted_at": utc_now(),
    }
    case_scheduler["attempted_directions"].append(direction)
    store.save_case(workspace, case, event={"type": "direction_attempted", "case_id": case_id, "direction_id": direction["id"]})
    return direction


def add_next_action(
    workspace: str | Path | None,
    case_id: str,
    description: str,
    assigned_role: str,
    priority: float,
    reason: str,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    case_scheduler = ensure_scheduler(case)
    action = {
        "id": new_id("act"),
        "description": description,
        "assigned_role": assigned_role,
        "priority": float(priority),
        "reason": reason,
        "status": "pending",
        "created_at": utc_now(),
    }
    case_scheduler["next_actions"].append(action)
    case_scheduler["next_actions"].sort(key=lambda item: item["priority"], reverse=True)
    store.save_case(workspace, case, event={"type": "next_action_added", "case_id": case_id, "action_id": action["id"]})
    return action
```

- [ ] **Step 4: Run scheduler tests**

Run:

```bash
uv run pytest tests/test_scheduler.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/scheduler.py plugins/detective-plugin/tests/test_scheduler.py
git commit -m "feat: track detective investigation scheduling"
```

## Task 3: Implement candidate action scoring and user guidance capture

**Files:**
- Modify: `plugins/detective-plugin/tests/test_scheduler.py`
- Modify: `plugins/detective-plugin/detective_mcp/scheduler.py`

- [ ] **Step 1: Add failing scoring and guidance tests**

Append to `plugins/detective-plugin/tests/test_scheduler.py`:

```python

def test_score_candidate_actions_applies_cold_direction_penalty(tmp_path):
    store.open_case(tmp_path, "Score", "Description", case_id="score")
    hypothesis = store.add_node(tmp_path, "score", "hypothesis", "Cache issue")
    scheduler.record_direction_attempt(tmp_path, "score", "Check cache", [hypothesis["id"]], 0)
    scheduler.record_direction_attempt(tmp_path, "score", "Check cache", [hypothesis["id"]], 0)
    scheduler.record_direction_attempt(tmp_path, "score", "Check cache", [hypothesis["id"]], 0)

    scored = scheduler.score_candidate_actions(
        tmp_path,
        "score",
        [
            {
                "description": "Check cache",
                "target_node_ids": [hypothesis["id"]],
                "information_gain": 0.9,
                "feasibility": 0.9,
                "urgency": 0.9,
                "cost": 1,
            },
            {
                "description": "Read deployment notes",
                "target_node_ids": [hypothesis["id"]],
                "information_gain": 0.5,
                "feasibility": 0.8,
                "urgency": 0.5,
                "cost": 2,
            },
        ],
    )

    assert scored[0]["description"] == "Read deployment notes"
    assert scored[1]["cold_direction"] is True


def test_apply_user_guidance_creates_high_priority_graph_state(tmp_path):
    store.open_case(tmp_path, "Guidance", "Description", case_id="guidance")

    result = scheduler.apply_user_guidance(
        tmp_path,
        "guidance",
        guidance_type="constraint",
        content="Do not use external web search for this case",
    )

    node = result["node"]
    assert node["type"] == "constraint"
    assert node["source"] == "user"
    assert node["confidence"] == 1.0
    assert node["metadata"]["user_override"] is True
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_scheduler.py -v
```

Expected: FAIL because scoring and user guidance functions are missing.

- [ ] **Step 3: Implement scoring and guidance**

Append to `plugins/detective-plugin/detective_mcp/scheduler.py`:

```python

def _matching_cold_direction(case_scheduler: dict[str, Any], description: str, target_node_ids: list[str]) -> bool:
    for direction in case_scheduler["attempted_directions"]:
        if direction["status"] == "cold" and _same_direction(direction, description, target_node_ids):
            return True
    return False


def score_candidate_actions(
    workspace: str | Path | None,
    case_id: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case = store.load_case(workspace, case_id)
    case_scheduler = ensure_scheduler(case)
    scored = []
    for candidate in candidates:
        cost = max(float(candidate.get("cost", 5)), 0.1)
        score = (
            float(candidate.get("information_gain", 0.5))
            * float(candidate.get("feasibility", 0.5))
            * float(candidate.get("urgency", 0.5))
            / cost
        )
        cold = _matching_cold_direction(
            case_scheduler,
            candidate["description"],
            candidate.get("target_node_ids", []),
        )
        if cold:
            score *= 0.1
        scored.append({**candidate, "score": round(score, 4), "cold_direction": cold})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def apply_user_guidance(
    workspace: str | Path | None,
    case_id: str,
    guidance_type: str,
    content: str,
) -> dict[str, Any]:
    mapping = {
        "fact": "evidence",
        "theory": "hypothesis",
        "constraint": "constraint",
        "question": "question",
    }
    node_type = mapping.get(guidance_type, "observation")
    confidence = 1.0 if node_type in {"evidence", "constraint"} else 0.8
    node = store.add_node(
        workspace,
        case_id,
        node_type=node_type,
        content=content,
        status="open",
        confidence=confidence,
        source="user",
        tags=["user-guidance"],
        created_by="user",
        metadata={"user_override": True, "guidance_type": guidance_type},
    )
    return {"case_id": case_id, "node": node, "policy": "user_guidance_has_priority"}
```

- [ ] **Step 4: Run scheduler tests**

Run:

```bash
uv run pytest tests/test_scheduler.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/scheduler.py plugins/detective-plugin/tests/test_scheduler.py
git commit -m "feat: score detective actions and capture user guidance"
```

## Task 4: Implement convergence and deadlock signals

**Files:**
- Create: `plugins/detective-plugin/tests/test_signals.py`
- Create: `plugins/detective-plugin/detective_mcp/signals.py`

- [ ] **Step 1: Write failing signal tests**

Create `plugins/detective-plugin/tests/test_signals.py`:

```python
from detective_mcp import scheduler, signals, store


def test_convergence_false_when_open_question_requires_hypothesis(tmp_path):
    store.open_case(tmp_path, "Not Done", "Description", case_id="not-done")
    evidence = store.add_node(tmp_path, "not-done", "evidence", "Strong evidence", confidence=1.0)
    hypothesis = store.add_node(tmp_path, "not-done", "hypothesis", "Likely answer", confidence=0.9)
    question = store.add_node(tmp_path, "not-done", "question", "Blocking unknown", confidence=0.9)
    store.add_edge(tmp_path, "not-done", evidence["id"], hypothesis["id"], "supports")
    store.add_edge(tmp_path, "not-done", question["id"], hypothesis["id"], "requires")

    result = signals.convergence_status(tmp_path, "not-done")

    assert result["converged"] is False
    assert "1 blocking open question" in result["reason"]


def test_convergence_true_with_supported_hypothesis_and_rejected_alternative(tmp_path):
    store.open_case(tmp_path, "Done", "Description", case_id="done")
    evidence = store.add_node(tmp_path, "done", "evidence", "Strong evidence", confidence=1.0)
    winner = store.add_node(tmp_path, "done", "hypothesis", "Correct answer", confidence=0.9)
    loser = store.add_node(tmp_path, "done", "hypothesis", "Wrong answer", confidence=0.1, status="rejected")
    store.add_edge(tmp_path, "done", evidence["id"], winner["id"], "supports")

    result = signals.convergence_status(tmp_path, "done")

    assert result["converged"] is True
    assert result["recommendation"] == "close-case"


def test_deadlock_true_when_all_scores_low_and_recent_actions_empty(tmp_path):
    store.open_case(tmp_path, "Deadlock", "Description", case_id="deadlock")
    result = signals.deadlock_status(
        tmp_path,
        "deadlock",
        scored_actions=[{"description": "weak", "score": 0.1}],
        recent_new_nodes=0,
        recent_new_edges=0,
    )

    assert result["deadlocked"] is True
    assert "all candidate actions below" in result["reason"]


def test_deadlock_false_when_high_score_action_exists(tmp_path):
    store.open_case(tmp_path, "Not Dead", "Description", case_id="not-dead")
    result = signals.deadlock_status(
        tmp_path,
        "not-dead",
        scored_actions=[{"description": "useful", "score": 0.8}],
        recent_new_nodes=0,
        recent_new_edges=0,
    )

    assert result["deadlocked"] is False
```

- [ ] **Step 2: Run signal tests to verify failure**

Run:

```bash
uv run pytest tests/test_signals.py -v
```

Expected: FAIL because `signals.py` does not exist.

- [ ] **Step 3: Implement signals**

Create `plugins/detective-plugin/detective_mcp/signals.py`:

```python
from pathlib import Path
from typing import Any

from . import store


def convergence_status(workspace: str | Path | None, case_id: str) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    config = case.get("config", {})
    confirm = config.get("confidence_threshold_confirm", 0.85)
    eliminate = config.get("confidence_threshold_eliminate", 0.15)
    nodes = case["nodes"]
    edges = case["edges"]

    hypotheses = [node for node in nodes if node["type"] == "hypothesis"]
    active = [node for node in hypotheses if node["status"] not in {"rejected", "stale", "resolved"}]
    confirmed = [node for node in active if node["confidence"] >= confirm]
    alternatives_open = [node for node in active if node not in confirmed and node["confidence"] >= eliminate]

    supporting_targets = {
        edge["to_id"]
        for edge in edges
        if edge["type"] == "supports"
        and any(node["id"] == edge["from_id"] and node["type"] == "evidence" for node in nodes)
    }
    confirmed_with_support = [node for node in confirmed if node["id"] in supporting_targets]

    blocking_questions = []
    for edge in edges:
        if edge["type"] != "requires":
            continue
        source = next((node for node in nodes if node["id"] == edge["from_id"]), None)
        target_is_confirmed = any(node["id"] == edge["to_id"] for node in confirmed)
        if source and source["type"] == "question" and source["status"] == "open" and target_is_confirmed:
            blocking_questions.append(source)

    converged = bool(confirmed_with_support) and not alternatives_open and not blocking_questions
    if converged:
        reason = "Confirmed hypothesis has evidence support, alternatives are resolved, and no blocking open questions remain"
    elif blocking_questions:
        reason = f"Not converged: {len(blocking_questions)} blocking open question(s) remain"
    elif not confirmed_with_support:
        reason = "Not converged: no confirmed hypothesis has direct evidence support"
    else:
        reason = f"Not converged: {len(alternatives_open)} alternative hypothesis(es) still active"

    return {
        "case_id": case_id,
        "converged": converged,
        "confirmed_hypotheses": confirmed_with_support,
        "blocking_questions": blocking_questions,
        "alternatives_open": alternatives_open,
        "reason": reason,
        "recommendation": "close-case" if converged else "continue-investigation",
    }


def deadlock_status(
    workspace: str | Path | None,
    case_id: str,
    scored_actions: list[dict[str, Any]],
    recent_new_nodes: int = 0,
    recent_new_edges: int = 0,
) -> dict[str, Any]:
    case = store.load_case(workspace, case_id)
    threshold = case.get("config", {}).get("deadlock_score_threshold", 0.3)
    has_actions = bool(scored_actions)
    all_low = has_actions and all(float(action.get("score", 0.0)) < threshold for action in scored_actions)
    no_recent_graph_change = recent_new_nodes == 0 and recent_new_edges == 0
    deadlocked = all_low and no_recent_graph_change
    if deadlocked:
        reason = f"Deadlocked: all candidate actions below {threshold} and recent investigation produced no graph changes"
    elif not has_actions:
        reason = "Not deadlocked: no candidate actions were provided for evaluation"
    else:
        reason = "Not deadlocked: at least one candidate action remains viable or recent graph changes exist"
    return {
        "case_id": case_id,
        "deadlocked": deadlocked,
        "reason": reason,
        "recommendation": "discuss-case" if deadlocked else "continue-investigation",
    }
```

- [ ] **Step 4: Run signal tests**

Run:

```bash
uv run pytest tests/test_signals.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/signals.py plugins/detective-plugin/tests/test_signals.py
git commit -m "feat: detect detective convergence and deadlock"
```

## Task 5: Expose v2.1 MCP tools

**Files:**
- Modify: `plugins/detective-plugin/tests/test_server_tools.py`
- Modify: `plugins/detective-plugin/detective_mcp/server.py`

- [ ] **Step 1: Add failing server tests for v2.1 tools**

Append to `plugins/detective-plugin/tests/test_server_tools.py`:

```python

def test_server_exposes_scheduler_and_signal_tools(tmp_path):
    server.detective_open_case("Signals", "Description", case_id="signals", workspace=str(tmp_path))
    hypothesis = server.detective_add_node("signals", "hypothesis", "Maybe config", workspace=str(tmp_path))

    direction = server.detective_record_direction_attempt(
        "signals",
        "Check config",
        [hypothesis["id"]],
        0,
        workspace=str(tmp_path),
    )
    action = server.detective_add_next_action(
        "signals",
        "Read config file",
        "evidence-hunter",
        0.7,
        "Tests current hypothesis",
        workspace=str(tmp_path),
    )
    scored = server.detective_score_candidate_actions(
        "signals",
        [{"description": "Read config file", "target_node_ids": [hypothesis["id"]], "information_gain": 0.8, "feasibility": 0.9, "urgency": 0.7, "cost": 1}],
        workspace=str(tmp_path),
    )
    guidance = server.detective_apply_user_guidance("signals", "fact", "User observed this yesterday", workspace=str(tmp_path))
    convergence = server.detective_convergence_status("signals", workspace=str(tmp_path))
    deadlock = server.detective_deadlock_status("signals", scored, workspace=str(tmp_path))

    assert direction["description"] == "Check config"
    assert action["assigned_role"] == "evidence-hunter"
    assert scored[0]["score"] > 0
    assert guidance["node"]["source"] == "user"
    assert convergence["recommendation"] in {"close-case", "continue-investigation"}
    assert deadlock["recommendation"] in {"discuss-case", "continue-investigation"}
```

- [ ] **Step 2: Run server tests to verify failure**

Run:

```bash
uv run pytest tests/test_server_tools.py -v
```

Expected: FAIL because v2.1 tool wrappers are missing.

- [ ] **Step 3: Add imports to server**

Modify the import section of `plugins/detective-plugin/detective_mcp/server.py`:

```python
from . import exports, graph, scheduler, signals, store
```

- [ ] **Step 4: Add v2.1 tools to server**

Append to `plugins/detective-plugin/detective_mcp/server.py` before the `if __name__ == "__main__"` block:

```python

@mcp.tool()
def detective_record_direction_attempt(
    case_id: str,
    description: str,
    target_node_ids: list[str],
    new_evidence_count: int,
    workspace: str | None = None,
) -> dict[str, Any]:
    return scheduler.record_direction_attempt(workspace, case_id, description, target_node_ids, new_evidence_count)


@mcp.tool()
def detective_add_next_action(
    case_id: str,
    description: str,
    assigned_role: str,
    priority: float,
    reason: str,
    workspace: str | None = None,
) -> dict[str, Any]:
    return scheduler.add_next_action(workspace, case_id, description, assigned_role, priority, reason)


@mcp.tool()
def detective_score_candidate_actions(
    case_id: str,
    candidates: list[dict[str, Any]],
    workspace: str | None = None,
) -> list[dict[str, Any]]:
    return scheduler.score_candidate_actions(workspace, case_id, candidates)


@mcp.tool()
def detective_apply_user_guidance(
    case_id: str,
    guidance_type: str,
    content: str,
    workspace: str | None = None,
) -> dict[str, Any]:
    return scheduler.apply_user_guidance(workspace, case_id, guidance_type, content)


@mcp.tool()
def detective_convergence_status(case_id: str, workspace: str | None = None) -> dict[str, Any]:
    return signals.convergence_status(workspace, case_id)


@mcp.tool()
def detective_deadlock_status(
    case_id: str,
    scored_actions: list[dict[str, Any]],
    recent_new_nodes: int = 0,
    recent_new_edges: int = 0,
    workspace: str | None = None,
) -> dict[str, Any]:
    return signals.deadlock_status(workspace, case_id, scored_actions, recent_new_nodes, recent_new_edges)
```

- [ ] **Step 5: Run server tests**

Run:

```bash
uv run pytest tests/test_server_tools.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/server.py plugins/detective-plugin/tests/test_server_tools.py
git commit -m "feat: expose detective autonomous investigation tools"
```

## Task 6: Enhance Markdown and Mermaid exports for v2.1

**Files:**
- Modify: `plugins/detective-plugin/tests/test_exports.py`
- Modify: `plugins/detective-plugin/detective_mcp/exports.py`

- [ ] **Step 1: Add failing enhanced export tests**

Append to `plugins/detective-plugin/tests/test_exports.py`:

```python
from detective_mcp import scheduler


def test_markdown_export_includes_scheduler_and_agent_activity(tmp_path):
    build_export_case(tmp_path)
    scheduler.record_direction_attempt(tmp_path, "export-case", "Try stale path", [], 0)
    scheduler.record_direction_attempt(tmp_path, "export-case", "Try stale path", [], 0)
    scheduler.record_direction_attempt(tmp_path, "export-case", "Try stale path", [], 0)
    scheduler.add_next_action(tmp_path, "export-case", "Check contradiction", "contradiction-finder", 0.8, "Falsify leading hypothesis")

    result = exports.export_markdown(tmp_path, "export-case")
    text = Path(result["path"]).read_text()

    assert "## Scheduler" in text
    assert "Try stale path" in text
    assert "cold" in text
    assert "contradiction-finder" in text


def test_focused_mermaid_export_for_hypothesis_chain(tmp_path):
    observation, evidence, hypothesis = build_export_case(tmp_path)

    result = exports.export_mermaid(tmp_path, "export-case", diagram="hypothesis-chain", focus_node_id=hypothesis["id"])
    text = Path(result["path"]).read_text()

    assert "graph LR" in text
    assert hypothesis["id"] in text
    assert evidence["id"] in text
    assert "supports" in text
```

- [ ] **Step 2: Run export tests to verify failure**

Run:

```bash
uv run pytest tests/test_exports.py -v
```

Expected: FAIL because exports do not include scheduler sections or focused Mermaid options.

- [ ] **Step 3: Add scheduler section to Markdown export**

Modify `export_markdown()` in `plugins/detective-plugin/detective_mcp/exports.py` after Recent Actions section:

```python
    scheduler_state = case.get("scheduler", {"attempted_directions": [], "next_actions": []})
    lines.extend(["", "## Scheduler", "", "### Attempted Directions", ""])
    if scheduler_state["attempted_directions"]:
        for direction in scheduler_state["attempted_directions"]:
            lines.append(
                f"- `{direction['id']}` {direction['description']} "
                f"(attempts: {direction['attempts']}, status: {direction['status']}, "
                f"new evidence: {direction['new_evidence_count']})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "### Next Actions", ""])
    if scheduler_state["next_actions"]:
        for action in scheduler_state["next_actions"]:
            lines.append(
                f"- `{action['id']}` {action['description']} "
                f"(role: {action['assigned_role']}, priority: {action['priority']:.2f}, status: {action['status']}) — {action['reason']}"
            )
    else:
        lines.append("- None")
```

- [ ] **Step 4: Add focused Mermaid parameters**

Change `export_mermaid` signature in `plugins/detective-plugin/detective_mcp/exports.py`:

```python
def export_mermaid(
    workspace: str | Path | None,
    case_id: str,
    diagram: str = "full",
    focus_node_id: str | None = None,
) -> dict[str, str]:
```

Inside `export_mermaid`, replace direct node/edge iteration with:

```python
    selected_edges = case["edges"]
    if diagram == "hypothesis-chain" and focus_node_id:
        selected_edges = [
            edge for edge in case["edges"]
            if edge["to_id"] == focus_node_id or edge["from_id"] == focus_node_id
        ]
        selected_node_ids = {focus_node_id}
        for edge in selected_edges:
            selected_node_ids.add(edge["from_id"])
            selected_node_ids.add(edge["to_id"])
        selected_nodes = [node for node in case["nodes"] if node["id"] in selected_node_ids]
    else:
        selected_nodes = case["nodes"]
```

Then iterate `selected_nodes` and `selected_edges` instead of `case["nodes"]` and `case["edges"]`.

- [ ] **Step 5: Update server wrapper for Mermaid export**

Modify `detective_export_mermaid()` in `plugins/detective-plugin/detective_mcp/server.py`:

```python
@mcp.tool()
def detective_export_mermaid(
    case_id: str,
    diagram: str = "full",
    focus_node_id: str | None = None,
    workspace: str | None = None,
) -> dict[str, str]:
    return exports.export_mermaid(workspace, case_id, diagram, focus_node_id)
```

- [ ] **Step 6: Run export tests**

Run:

```bash
uv run pytest tests/test_exports.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/detective_mcp/exports.py plugins/detective-plugin/detective_mcp/server.py plugins/detective-plugin/tests/test_exports.py
git commit -m "feat: enrich detective investigation exports"
```

## Task 7: Add specialist agents

**Files:**
- Create: `plugins/detective-plugin/agents/lead-investigator.md`
- Create: `plugins/detective-plugin/agents/hypothesis-generator.md`
- Create: `plugins/detective-plugin/agents/evidence-hunter.md`
- Create: `plugins/detective-plugin/agents/contradiction-finder.md`
- Create: `plugins/detective-plugin/agents/path-analyzer.md`
- Create: `plugins/detective-plugin/agents/report-writer.md`

- [ ] **Step 1: Create lead investigator agent**

Create `plugins/detective-plugin/agents/lead-investigator.md`:

```markdown
---
description: Use this agent to coordinate a Detective v2.1 investigation loop over an active MCP-backed case. It reads graph overview, plans next actions, dispatches specialist agents when appropriate, records findings through MCP tools, and pauses on convergence, deadlock, budget exhaustion, or user intervention.
tools: TaskList, TaskGet, TaskUpdate, Agent, mcp__plugin_detective_detective__detective_graph_overview, mcp__plugin_detective_detective__detective_list_nodes, mcp__plugin_detective_detective__detective_search_nodes, mcp__plugin_detective_detective__detective_score_candidate_actions, mcp__plugin_detective_detective__detective_add_next_action, mcp__plugin_detective_detective__detective_record_direction_attempt, mcp__plugin_detective_detective__detective_convergence_status, mcp__plugin_detective_detective__detective_deadlock_status, mcp__plugin_detective_detective__detective_export_markdown, mcp__plugin_detective_detective__detective_export_mermaid
---

You are the lead investigator for Detective v2.1.

Process:
1. Read the case overview with `detective_graph_overview`.
2. List active hypotheses, open questions, and evidence gaps.
3. Generate 2-5 candidate next actions.
4. Score them with `detective_score_candidate_actions`.
5. Dispatch specialist agents only when tasks are independent.
6. Require every specialist finding to be written through MCP tools, never by editing JSON directly.
7. Check convergence and deadlock after each round.
8. Export Markdown and Mermaid after meaningful graph changes.

Stop and report when convergence, deadlock, budget exhaustion, or explicit user intervention occurs.
```

- [ ] **Step 2: Create hypothesis generator agent**

Create `plugins/detective-plugin/agents/hypothesis-generator.md`:

```markdown
---
description: Use this agent to generate candidate hypotheses from observations, clues, open questions, and existing evidence in a Detective MCP case.
tools: mcp__plugin_detective_detective__detective_graph_overview, mcp__plugin_detective_detective__detective_list_nodes, mcp__plugin_detective_detective__detective_add_node, mcp__plugin_detective_detective__detective_add_edge
---

You generate hypotheses for an active Detective case.

Rules:
- Read observations, clues, evidence, and questions before proposing hypotheses.
- Add each hypothesis as a `hypothesis` node.
- Link it to source observations or questions with `derives` edges.
- Include confidence and rationale in metadata.
- Do not edit `.detective/` files directly.
```

- [ ] **Step 3: Create evidence hunter agent**

Create `plugins/detective-plugin/agents/evidence-hunter.md`:

```markdown
---
description: Use this agent to find evidence for or against active hypotheses in a Detective MCP case.
tools: Read, Bash, WebSearch, mcp__plugin_detective_detective__detective_list_nodes, mcp__plugin_detective_detective__detective_search_nodes, mcp__plugin_detective_detective__detective_add_node, mcp__plugin_detective_detective__detective_add_edge
---

You gather evidence for an active Detective case.

Rules:
- Start from active hypotheses or assigned target nodes.
- Use local files and approved external tools only when relevant.
- Add findings as `evidence` or `clue` nodes.
- Connect findings with `supports`, `contradicts`, or `related_to` edges.
- Include source metadata so the lead investigator can verify provenance.
- Do not edit `.detective/` files directly.
```

- [ ] **Step 4: Create contradiction finder agent**

Create `plugins/detective-plugin/agents/contradiction-finder.md`:

```markdown
---
description: Use this agent to try to falsify strong hypotheses, identify contradictions, and add constraints in a Detective MCP case.
tools: Read, Bash, WebSearch, mcp__plugin_detective_detective__detective_list_nodes, mcp__plugin_detective_detective__detective_neighbors, mcp__plugin_detective_detective__detective_add_node, mcp__plugin_detective_detective__detective_add_edge
---

You look for reasons a hypothesis might be wrong.

Rules:
- Focus on high-confidence hypotheses first.
- Add contradicting facts as `evidence` nodes.
- Add hard disqualifiers as `constraint` nodes.
- Connect contradictions with `contradicts` or `eliminates` edges.
- If falsification is inconclusive, add an open `question` node.
- Do not edit `.detective/` files directly.
```

- [ ] **Step 5: Create path analyzer agent**

Create `plugins/detective-plugin/agents/path-analyzer.md`:

```markdown
---
description: Use this agent to inspect graph topology, shortest paths, weak evidence chains, isolated nodes, and missing links in a Detective MCP case.
tools: mcp__plugin_detective_detective__detective_graph_overview, mcp__plugin_detective_detective__detective_list_nodes, mcp__plugin_detective_detective__detective_list_edges, mcp__plugin_detective_detective__detective_neighbors, mcp__plugin_detective_detective__detective_shortest_path, mcp__plugin_detective_detective__detective_add_node, mcp__plugin_detective_detective__detective_add_edge
---

You analyze Detective graph topology.

Rules:
- Identify isolated nodes and weak chains.
- Use shortest paths to explain how observations connect to hypotheses.
- Add `question` nodes for missing links.
- Add `task` nodes for graph repair actions.
- Do not edit `.detective/` files directly.
```

- [ ] **Step 6: Create report writer agent**

Create `plugins/detective-plugin/agents/report-writer.md`:

```markdown
---
description: Use this agent to generate or refresh Detective Markdown/Mermaid review artifacts and resolution drafts from MCP graph state.
tools: mcp__plugin_detective_detective__detective_graph_overview, mcp__plugin_detective_detective__detective_list_nodes, mcp__plugin_detective_detective__detective_list_edges, mcp__plugin_detective_detective__detective_export_markdown, mcp__plugin_detective_detective__detective_export_mermaid, mcp__plugin_detective_detective__detective_convergence_status
---

You produce readable investigation artifacts from graph state.

Rules:
- Use MCP export tools for files.
- Summarize the leading conclusion, evidence chain, contradictions, and unresolved questions.
- Do not invent evidence missing from the graph.
- Do not edit `.detective/` files directly.
```

- [ ] **Step 7: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/agents/lead-investigator.md plugins/detective-plugin/agents/hypothesis-generator.md plugins/detective-plugin/agents/evidence-hunter.md plugins/detective-plugin/agents/contradiction-finder.md plugins/detective-plugin/agents/path-analyzer.md plugins/detective-plugin/agents/report-writer.md
git commit -m "feat: add detective specialist agents"
```

## Task 8: Update skills to prefer MCP tools

**Files:**
- Modify: `plugins/detective-plugin/skills/investigate/SKILL.md`
- Modify: `plugins/detective-plugin/skills/review-board/SKILL.md`
- Modify: `plugins/detective-plugin/skills/discuss-case/SKILL.md`
- Modify: `plugins/detective-plugin/skills/close-case/SKILL.md`

- [ ] **Step 1: Update investigate skill**

Replace the opening process description in `plugins/detective-plugin/skills/investigate/SKILL.md` with:

```markdown
# Investigate — MCP-Backed Detective Loop

Execute the investigation cycle on an active MCP-backed case. Prefer Detective MCP tools over direct JSON edits or legacy scripts.

## Prerequisites

An active case must exist under `.detective/cases/`. If the MCP server is unavailable, explain that v2.1 investigation requires the detective MCP server and ask the user to check `/mcp`.

## Loop

1. Call `detective_graph_overview`.
2. List active hypotheses, open questions, and recent evidence with `detective_list_nodes`.
3. Generate candidate actions and call `detective_score_candidate_actions`.
4. In `full_auto`, dispatch specialist agents for independent actions; in `checkpoint`, run up to the checkpoint interval; in `manual`, ask the user before acting.
5. Require all findings to be written through MCP tools.
6. Call `detective_convergence_status` and `detective_deadlock_status`.
7. Export Markdown and Mermaid with `detective_export_markdown` and `detective_export_mermaid` after meaningful graph changes.
8. Stop on convergence, deadlock, budget exhaustion, or user intervention.
```

Keep the existing detailed v1 loop below this section under a heading `## Legacy script fallback`.

- [ ] **Step 2: Update review-board skill**

Add this section near the top of `plugins/detective-plugin/skills/review-board/SKILL.md`:

```markdown
## MCP-first review

For Detective v2 cases, prefer MCP tools:

1. `detective_graph_overview`
2. `detective_list_nodes`
3. `detective_list_edges`
4. `detective_convergence_status`
5. `detective_export_markdown`
6. `detective_export_mermaid`

Only use legacy scripts if the MCP server is unavailable.
```

- [ ] **Step 3: Update discuss-case skill**

Add this section near the top of `plugins/detective-plugin/skills/discuss-case/SKILL.md`:

```markdown
## MCP-first user guidance

When the user provides guidance, write it through `detective_apply_user_guidance`:

- Facts → `guidance_type="fact"`
- Theories → `guidance_type="theory"`
- Boundaries or disallowed directions → `guidance_type="constraint"`
- New uncertainties → `guidance_type="question"`

After applying guidance, call `detective_graph_overview` before continuing. User guidance has priority over automated scheduling.
```

- [ ] **Step 4: Update close-case skill**

Add this section near the top of `plugins/detective-plugin/skills/close-case/SKILL.md`:

```markdown
## MCP-first closing

For Detective v2 cases:

1. Call `detective_convergence_status`.
2. If converged, call `detective_export_markdown` and `detective_export_mermaid`.
3. If not converged, present unmet conditions and ask whether to continue, discuss, or force a partial close.
4. Do not edit `case.json` directly.
```

- [ ] **Step 5: Validate skill text mentions MCP tools**

Run:

```bash
grep -R "detective_graph_overview\|detective_apply_user_guidance\|detective_convergence_status" -n skills
```

Expected: output includes the modified skill files.

- [ ] **Step 6: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/skills/investigate/SKILL.md plugins/detective-plugin/skills/review-board/SKILL.md plugins/detective-plugin/skills/discuss-case/SKILL.md plugins/detective-plugin/skills/close-case/SKILL.md
git commit -m "docs: make detective skills MCP-first"
```

## Task 9: Document v2.1 automation

**Files:**
- Modify: `plugins/detective-plugin/README.md`
- Modify: `plugins/detective-plugin/README-zh.md`
- Modify: `plugins/detective-plugin/.claude-plugin/plugin.json`

- [ ] **Step 1: Bump plugin metadata to v0.3.0**

Modify `plugins/detective-plugin/.claude-plugin/plugin.json` version to `0.3.0` and description to:

```json
"description": "A general-purpose AI investigation framework with a local MCP graph core and autonomous investigation support. Maintains project-local CaseBoard state under .detective/, supports evidence chains, graph search, shortest paths, Markdown/Mermaid exports, scheduler memory, specialist agents, convergence signals, and user-priority guidance."
```

- [ ] **Step 2: Add English v2.1 README section**

Add to `plugins/detective-plugin/README.md` after the v2 MCP section:

```markdown
## v2.1 Autonomous Investigation

Detective v2.1 adds orchestration support on top of the MCP graph core.

New capabilities:

- Case-local scheduler memory for attempted directions and next actions
- Candidate action scoring
- Cold direction detection
- User guidance capture with priority over automation
- Conservative convergence status
- Deadlock status
- Specialist agents for hypotheses, evidence, contradictions, graph paths, and reporting

Default autonomy is `full_auto`, but user intervention always takes priority. The MCP server remains the state owner; agents and skills must use MCP tools rather than editing `.detective/` files directly.
```

- [ ] **Step 3: Add Chinese v2.1 README section**

Add to `plugins/detective-plugin/README-zh.md` after the v2 MCP section:

```markdown
## v2.1 自治调查

Detective v2.1 在 MCP 图核心之上增加自治调查编排能力。

新增能力：

- 案件本地调度记忆：记录已尝试方向和下一步动作
- 候选动作评分
- 冷线索/冷方向检测
- 用户指导优先写入图状态
- 保守的收敛状态判断
- 死锁状态判断
- 用于假设、证据、反证、图路径和报告的专用 agents

默认自治级别是 `full_auto`，但用户主动介入始终优先。MCP 服务仍然是状态所有者；agents 和 skills 必须通过 MCP 工具读写状态，不能直接编辑 `.detective/` 文件。
```

- [ ] **Step 4: Validate README mentions v2.1**

Run from `plugins/detective-plugin`:

```bash
grep -R "v2.1\|Autonomous Investigation\|自治调查" -n README.md README-zh.md .claude-plugin/plugin.json
```

Expected: output includes all three files.

- [ ] **Step 5: Commit checkpoint if commits are authorized**

```bash
git add plugins/detective-plugin/README.md plugins/detective-plugin/README-zh.md plugins/detective-plugin/.claude-plugin/plugin.json
git commit -m "docs: document detective autonomous investigation"
```

## Task 10: Final validation for v2.1

**Files:**
- Verify all v2.1 files.

- [ ] **Step 1: Run all tests**

Run from `plugins/detective-plugin`:

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run focused test files**

Run:

```bash
uv run pytest tests/test_scheduler.py tests/test_signals.py tests/test_server_tools.py tests/test_exports.py -v
```

Expected: all tests PASS.

- [ ] **Step 3: Validate agent files exist**

Run:

```bash
ls agents/lead-investigator.md agents/hypothesis-generator.md agents/evidence-hunter.md agents/contradiction-finder.md agents/path-analyzer.md agents/report-writer.md
```

Expected: all six paths print.

- [ ] **Step 4: Validate MCP server imports**

Run:

```bash
uv run python -c "from detective_mcp.server import detective_convergence_status, detective_score_candidate_actions; print('ok')"
```

Expected:

```text
ok
```

- [ ] **Step 5: Validate no direct JSON editing guidance was added**

Run:

```bash
grep -R "edit.*case.json\|directly edit.*\.detective" -n agents skills README.md README-zh.md || true
```

Expected: no output that instructs agents to directly edit case JSON. Mentions that direct editing is disallowed are acceptable.

- [ ] **Step 6: Check git diff**

Run from repository root:

```bash
git diff -- plugins/detective-plugin docs/superpowers/specs docs/superpowers/plans
```

Expected: diff contains only intended Detective v2/v2.1 code, tests, docs, specs, and plans.

- [ ] **Step 7: Manual Claude Code MCP check**

Restart Claude Code or reload plugins, run `/mcp`, and verify the detective server exposes v2.1 tools including:

- `detective_record_direction_attempt`
- `detective_add_next_action`
- `detective_score_candidate_actions`
- `detective_apply_user_guidance`
- `detective_convergence_status`
- `detective_deadlock_status`

- [ ] **Step 8: Final commit if commits are authorized**

```bash
git add plugins/detective-plugin docs/superpowers/specs docs/superpowers/plans
git commit -m "feat: add detective autonomous investigation support"
```
