import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
AGENTS = ROOT / "agents"
REFERENCE = SKILLS / "references" / "detective-core-protocol.md"
SKILL_NAMES = ["brainstorm", "open-case", "investigate", "discuss-case", "review-board", "close-case"]
ATTENTION_MD_PATHS = [*SKILLS.glob("**/*.md"), *AGENTS.glob("**/*.md")]
ALLOWED_ATTENTION_TAGS = {"HARD_GATE", "IMPORTANT"}
ATTENTION_OPEN_RE = re.compile(r"<(HARD_GATE|IMPORTANT)\s+name=\"([a-z0-9]+(?:-[a-z0-9]+)*)\">([\s\S]*?)</\1>")
XMLISH_TAG_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9_-]*)(?:\s[^>]*)?>")
LEGACY_ATTENTION_RE = re.compile(r"</?(?:HARD-GATE|HARD_GATE_[A-Z0-9_]+|IMPORTANT_[A-Z0-9_]+)\b")


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
        '<HARD_GATE name="subagent-delegation">',
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


def test_each_skill_references_shared_protocol_and_uses_attention_wrappers():
    for name in SKILL_NAMES:
        text = read_skill(name)
        assert "../references/detective-core-protocol.md" in text
        assert '<HARD_GATE name="' in text or '<IMPORTANT name="' in text


def test_each_agent_with_mandatory_constraints_uses_attention_wrappers():
    for path in AGENTS.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "do not" in text.lower() or "must" in text.lower():
            assert '<HARD_GATE name="' in text or '<IMPORTANT name="' in text


def test_agent_tools_support_assigned_state_transitions():
    lead = (AGENTS / "lead-investigator.md").read_text(encoding="utf-8")
    contradiction = (AGENTS / "contradiction-finder.md").read_text(encoding="utf-8")
    report = (AGENTS / "report-writer.md").read_text(encoding="utf-8")
    for tool in [
        "detective_add_node",
        "detective_update_node",
        "detective_add_edge",
        "detective_blackboard_list",
        "detective_blackboard_add",
        "detective_coverage_add",
        "detective_coverage_update",
    ]:
        assert tool in lead
    assert "detective_update_node" in contradiction
    assert "detective_evaluate_proof" not in report
    assert "read-only completion gate" in report


def test_attention_xml_wrappers_are_current_valid_and_nonempty():
    for path in ATTENTION_MD_PATHS:
        text = path.read_text(encoding="utf-8")
        assert not LEGACY_ATTENTION_RE.search(text), f"legacy attention tag in {path}"

        tags = [match for match in XMLISH_TAG_RE.finditer(text) if match.group(1).startswith(("HARD", "IMPORTANT"))]
        stack: list[tuple[str, str]] = []
        for tag in tags:
            raw = tag.group(0)
            tag_name = tag.group(1)
            if raw.startswith("</"):
                assert stack, f"unmatched closing tag {raw} in {path}"
                expected_name, expected_raw = stack.pop()
                assert tag_name == expected_name, f"{expected_raw} closed by {raw} in {path}"
                continue

            assert tag_name in ALLOWED_ATTENTION_TAGS, f"invalid attention tag {raw} in {path}"
            assert re.fullmatch(rf'<{tag_name} name="[a-z0-9]+(?:-[a-z0-9]+)*">', raw), (
                f"attention tag must have nonempty kebab-case name in {path}: {raw}"
            )
            stack.append((tag_name, raw))
        assert not stack, f"unclosed attention tag(s) in {path}: {stack}"

        for match in ATTENTION_OPEN_RE.finditer(text):
            assert match.group(3).strip(), f"empty attention wrapper in {path}: {match.group(0)}"


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


def test_missing_sources_are_blockers_not_counterevidence():
    reference = REFERENCE.read_text(encoding="utf-8")
    investigate = read_skill("investigate")
    assert "does not contradict, eliminate, weaken, or reduce the confidence" in reference
    assert "Missing expected evidence proves only the source/coverage limitation" in investigate
    assert "independent evidence" in investigate


def test_investigate_repairs_existing_gate_state_without_duplicates():
    text = read_skill("investigate")
    assert "never create a second item with the same area" in text
    assert "original open `question` nodes" in text
    assert "do not add a separate answer question" in text
    assert "Re-read actions, questions, and coverage" in text
    assert "failed gate is feedback to repair existing state" in text


def test_investigate_constrains_subagent_delegation_and_inheritance():
    text = read_skill("investigate")
    assert '<HARD_GATE name="subagent-delegation">' in text
    assert "</HARD_GATE>" in text
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
