from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REFERENCE = SKILLS / "references" / "detective-core-protocol.md"
SKILL_NAMES = ["brainstorm", "open-case", "investigate", "discuss-case", "review-board", "close-case"]


def read_skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def description_of(text: str) -> str:
    lines = text.splitlines()
    for line in lines:
        if line.startswith("description: "):
            return line.removeprefix("description: ")
    raise AssertionError("missing description")


def test_shared_reference_contains_core_protocol_requirements():
    text = REFERENCE.read_text(encoding="utf-8")
    assert len(text.splitlines()) < 300
    for required in [
        "Detective MCP state is the only durable case truth",
        "Node types: `observation`, `clue`, `evidence`, `hypothesis`, `constraint`, `conclusion`, `question`, `task`",
        "Exactly one `hypothesis` has `status=\"confirmed\"`",
        "direct `supports` edge",
        "Use `detective_completion_gate(case_id=...)` as the read-only default",
        "Prefer SetGoal or an equivalent goal tool",
        "<DETECTIVE-STOP-FALLBACK status=\"active\" case-id=\"<case_id>\">",
        "Mid-cycle resume is allowed",
        "<HARD_GATE_SUBAGENT_DELEGATION>",
        "Subagents inherit the coordinator's evidence, state, scope, and closure constraints",
        "Cross-skill handoff matrix",
        "Exports are artifacts, not state",
    ]:
        assert required in text


def test_skill_descriptions_are_pushy_and_have_near_miss_exclusions():
    for name in SKILL_NAMES:
        description = description_of(read_skill(name))
        assert "The assistant should use this when" in description
        assert "Do not use" in description


def test_each_skill_keeps_paired_semantic_gates_without_attribute_dependent_emphasis():
    for name in SKILL_NAMES:
        text = read_skill(name)
        assert "../references/detective-core-protocol.md" in text
        assert "<HARD_GATE_" in text or "<IMPORTANT_" in text
        assert '<HARD-GATE name=' not in text
        assert '<IMPORTANT name=' not in text


def test_review_board_uses_completion_gate_read_only_by_default():
    text = read_skill("review-board")
    assert "Use `detective_completion_gate(case_id=\"<case id>\")` as the default read-only proof readiness check" in text
    assert "Do not call `detective_evaluate_proof` during routine review" in text


def test_investigate_states_mid_cycle_resume_and_proof_lifecycle():
    text = read_skill("investigate")
    assert "On mid-cycle resume" in text
    assert "exactly one confirmed hypothesis" in text
    assert "direct `supports` edge" in text
    assert "questions resolved/rejected" in text


def test_investigate_constrains_subagent_delegation_and_inheritance():
    text = read_skill("investigate")
    assert "<HARD_GATE_SUBAGENT_DELEGATION>" in text
    assert "</HARD_GATE_SUBAGENT_DELEGATION>" in text
    for required in [
        "case id",
        "OODA phase and action id",
        "allowed tools and read/write boundaries",
        "required Detective MCP writes",
        "expected return format",
        "stop conditions",
        "must obey the same evidence, state, scope, and closure gates",
        "never edit `.detective/` directly",
        "never",
        "force-close",
        "validate returned evidence and MCP state",
    ]:
        assert required in text


def test_discuss_case_user_facts_use_clue_verified_confirmed():
    text = read_skill("discuss-case")
    assert "type=\"clue\"" in text
    assert "status=\"verified\"" in text
    assert "status=\"confirmed\"" in text


def test_open_case_uses_current_signatures_and_default_slug_behavior():
    text = read_skill("open-case")
    assert 'detective_open_case(title="<title>", description="<description>", case_id=null, config=<budget_config>)' in text
    assert "let MCP generate numbering/slug" in text


def test_stop_fallback_markers_remain_dynamic_and_conditional():
    combined = "\n".join(read_skill(name) for name in SKILL_NAMES) + REFERENCE.read_text(encoding="utf-8")
    assert "Only when no goal tool is available" in combined
    assert "statically registered inert StopHook" in combined
    assert "Do not call SetGoal" in read_skill("brainstorm")
