import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS_JSON = ROOT / "hooks" / "hooks.json"
SKILLS = ROOT / "skills"
README = ROOT / "README.md"
README_ZH = ROOT / "README-zh.md"


def _stop_prompt() -> str:
    config = json.loads(HOOKS_JSON.read_text())
    return config["hooks"]["Stop"][0]["hooks"][0]["prompt"]


def _skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def test_hooks_json_uses_plugin_wrapper_format():
    config = json.loads(HOOKS_JSON.read_text())

    assert isinstance(config["description"], str)
    assert isinstance(config["hooks"], dict)
    assert set(config["hooks"]) == {"Stop"}

    stop_entry = config["hooks"]["Stop"][0]
    assert stop_entry["matcher"] == "*"
    hook = stop_entry["hooks"][0]
    assert hook["type"] == "prompt"
    assert isinstance(hook["prompt"], str)
    assert hook["timeout"] <= 30


def test_stop_prompt_requires_exact_decision_json_semantics():
    prompt = _stop_prompt()

    assert '"decision":"approve"|"block"' in prompt
    assert '"reason":"concise reason"' in prompt
    assert "Return only valid JSON" in prompt
    assert "Do not include markdown or extra keys" in prompt


def test_stop_prompt_is_inert_without_marker():
    prompt = _stop_prompt().lower()

    assert "inert by default" in prompt
    assert "no latest unmatched active" in prompt
    assert "immediately return" in prompt
    assert "detective stop fallback inactive" in prompt
    assert "do not infer activation" in prompt
    assert "open/active detective case" in prompt


def test_stop_prompt_defines_marker_protocol():
    prompt = _stop_prompt()

    assert '<DETECTIVE-STOP-FALLBACK status="active" case-id="CASE_ID">' in prompt
    assert '<DETECTIVE-STOP-FALLBACK status="inactive" case-id="CASE_ID" reason="REASON">' in prompt
    assert "latest marker wins per case id" in prompt
    assert "A later inactive marker for that case disengages it" in prompt
    assert "Do not read or edit files" in prompt


def test_stop_prompt_is_safe_fallback_not_blind_blocker():
    prompt = _stop_prompt().lower()

    assert "setgoal" in prompt
    assert "equivalent goal-driven continuation" in prompt
    assert "only a fallback" in prompt
    assert "no goal tool is available" in prompt
    assert "skills should emit active markers" in prompt


def test_stop_prompt_lists_approval_safety_conditions():
    prompt = _stop_prompt().lower()

    required = [
        "no latest unmatched active",
        "later inactive marker",
        "latest marker wins",
        "completion gate passed",
        "case closed",
        "user explicitly asked to stop",
        "pause",
        "user-only decision",
        "blocked",
        "no legal useful action remains",
        "no active detective case",
        "budget",
        "max_actions",
        "timebox",
        "setgoal or an equivalent goal-driven continuation mechanism",
        "tests/build/final non-detective task is complete",
        "repeated stophook blocks",
        "cycling",
        "fail-open",
    ]
    for text in required:
        assert text in prompt


def test_stop_prompt_blocks_only_unfinished_actionable_cases_without_goal_mechanism():
    prompt = _stop_prompt().lower()

    required = [
        "block stopping only when all of these are true",
        "latest marker for the selected case id is active",
        "unmatched by a later inactive marker",
        "active detective case/investigation",
        "same marker case id",
        "goal is unfinished",
        "detective_completion_gate has not passed",
        "concrete legal useful next ooda action remains",
        "no setgoal or equivalent goal-driven continuation mechanism",
        "no transcript evidence shows prior stophook block loops",
    ]
    for text in required:
        assert text in prompt


def test_skills_activate_fallback_only_when_goal_tool_unavailable():
    for name in ["open-case", "investigate"]:
        text = _skill(name)
        assert "SetGoal or equivalent goal tool" in text
        assert "Only when no goal tool is available" in text
        assert '<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">' in text
        assert "must not be written to `.detective/` files" in text


def test_brainstorm_does_not_activate_fallback_pre_approval():
    text = _skill("brainstorm")

    assert "<HARD_GATE_NO_STOP_FALLBACK_BEFORE_APPROVAL>" in text
    assert "</HARD_GATE_NO_STOP_FALLBACK_BEFORE_APPROVAL>" in text
    assert "Do not emit `<DETECTIVE-STOP-FALLBACK ...>` markers during brainstorm pre-approval" in text
    assert "only after a durable MCP case exists" in text


def test_review_and_discussion_preserve_or_deactivate_fallback():
    for name in ["review-board", "discuss-case"]:
        text = _skill(name)
        assert "<IMPORTANT_STOP_FALLBACK_STATUS_PRESERVATION>" in text
        assert "</IMPORTANT_STOP_FALLBACK_STATUS_PRESERVATION>" in text
        assert "preserves the current Stop fallback marker status" in text
        assert '<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>"' in text
        assert "Do not emit a new active marker" in text


def test_investigate_and_close_deactivate_on_stop_conditions():
    investigate = _skill("investigate")
    close_case = _skill("close-case")

    for reason in ["pause", "blocked", "budget-exhausted", "complete"]:
        assert reason in investigate
    assert '<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="<pause|blocked|budget-exhausted|complete|closed>">' in investigate

    assert "<HARD_GATE_STOP_FALLBACK_DEACTIVATION_ON_CLOSE>" in close_case
    assert "</HARD_GATE_STOP_FALLBACK_DEACTIVATION_ON_CLOSE>" in close_case
    assert '<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="closed">' in close_case
    assert '<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>" reason="blocked">' in close_case


def test_readmes_document_static_inert_fallback_and_no_hot_loading():
    for path in [README, README_ZH]:
        text = path.read_text()
        assert '<DETECTIVE-STOP-FALLBACK status="active" case-id="<case_id>">' in text
        assert '<DETECTIVE-STOP-FALLBACK status="inactive" case-id="<case_id>"' in text
        assert "latest" in text.lower() or "最新" in text
        assert "SetGoal" in text
        assert "hot" in text.lower() or "热" in text
        assert "restart" in text.lower() or "重启" in text
        assert "inert" in text.lower() or "惰性" in text
