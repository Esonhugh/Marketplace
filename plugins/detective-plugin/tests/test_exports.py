from pathlib import Path

import pytest

from detective_mcp import exports, scheduler, store


def build_export_case(tmp_path):
    store.open_case(tmp_path, "Export Case", "Readable artifacts", case_id="export-case")
    observation = store.add_node(tmp_path, "export-case", "observation", "Initial symptom", source="user")
    evidence = store.add_node(tmp_path, "export-case", "evidence", "Verified log line", source="file")
    hypothesis = store.add_node(
        tmp_path,
        "export-case",
        "hypothesis",
        "Log line explains symptom",
        source="agent",
        confidence=0.8,
    )
    store.add_edge(tmp_path, "export-case", observation["id"], evidence["id"], "derives")
    store.add_edge(
        tmp_path,
        "export-case",
        evidence["id"],
        hypothesis["id"],
        "supports",
        rationale="Log line matches symptom",
    )
    return observation, evidence, hypothesis


def test_export_markdown_writes_notes_file(tmp_path):
    build_export_case(tmp_path)

    result = exports.export_markdown(tmp_path, "export-case")

    path = Path(result["path"])
    assert path.name == "notes.md"
    text = path.read_text(encoding="utf-8")
    assert "# Case: Export Case" in text
    assert "## Active Hypotheses" in text
    assert "Log line explains symptom" in text
    assert "## Evidence" in text
    assert "Verified log line" in text
    assert "## Key Relationships" in text
    assert "supports" in text



def test_export_markdown_includes_scheduler_details(tmp_path):
    _, _, hypothesis = build_export_case(tmp_path)
    scheduler.record_direction_attempt(
        tmp_path,
        "export-case",
        description="Challenge primary theory",
        target_node_ids=[hypothesis["id"]],
        new_evidence_count=0,
    )
    scheduler.record_direction_attempt(
        tmp_path,
        "export-case",
        description="Challenge primary theory",
        target_node_ids=[hypothesis["id"]],
        new_evidence_count=0,
    )
    scheduler.record_direction_attempt(
        tmp_path,
        "export-case",
        description="Challenge primary theory",
        target_node_ids=[hypothesis["id"]],
        new_evidence_count=0,
    )
    scheduler.add_next_action(
        tmp_path,
        "export-case",
        "Try to falsify the leading hypothesis",
        "contradiction-finder",
        0.9,
        "Cold direction needs adversarial review",
    )

    result = exports.export_markdown(tmp_path, "export-case")

    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "## Scheduler" in text
    assert "### Attempted Directions" in text
    assert "Challenge primary theory" in text
    assert "status: cold" in text
    assert "new evidence: 0" in text
    assert "### Next Actions" in text
    assert "assigned role: contradiction-finder" in text
    assert "priority: 0.90" in text
    assert "reason: Cold direction needs adversarial review" in text


def test_export_mermaid_writes_graph_file(tmp_path):
    build_export_case(tmp_path)

    result = exports.export_mermaid(tmp_path, "export-case")

    path = Path(result["path"])
    assert path.name == "graph.mmd"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("graph LR")
    assert "Initial symptom" in text
    assert "-- supports -->" in text



def test_export_mermaid_hypothesis_chain_focuses_on_direct_connections(tmp_path):
    _, evidence, hypothesis = build_export_case(tmp_path)

    result = exports.export_mermaid(
        tmp_path,
        "export-case",
        diagram="hypothesis-chain",
        focus_node_id=hypothesis["id"],
    )

    text = Path(result["path"]).read_text(encoding="utf-8")
    assert hypothesis["id"] in text
    assert evidence["id"] in text
    assert "Log line explains symptom" in text
    assert "Verified log line" in text
    assert f'{evidence["id"]} -- supports --> {hypothesis["id"]}' in text



def test_export_mermaid_hypothesis_chain_excludes_unrelated_isolated_nodes(tmp_path):
    _, evidence, hypothesis = build_export_case(tmp_path)
    unrelated = store.add_node(tmp_path, "export-case", "evidence", "Unrelated breadcrumb", source="file")

    result = exports.export_mermaid(
        tmp_path,
        "export-case",
        diagram="hypothesis-chain",
        focus_node_id=hypothesis["id"],
    )

    text = Path(result["path"]).read_text(encoding="utf-8")
    assert evidence["id"] in text
    assert hypothesis["id"] in text
    assert unrelated["id"] not in text
    assert "Unrelated breadcrumb" not in text
    assert "Initial symptom" not in text


def test_export_preserves_unicode_literals_in_markdown_and_mermaid(tmp_path):
    store.open_case(tmp_path, "Unicode Case", "Readable artifacts", case_id="unicode-case")
    node = store.add_node(tmp_path, "unicode-case", "evidence", '证据 [alpha] "β"', source="file")

    markdown_result = exports.export_markdown(tmp_path, "unicode-case")
    mermaid_result = exports.export_mermaid(tmp_path, "unicode-case")

    markdown_text = Path(markdown_result["path"]).read_text(encoding="utf-8")
    mermaid_text = Path(mermaid_result["path"]).read_text(encoding="utf-8")

    assert '证据 [alpha] "β"' in markdown_text
    assert node["id"] in mermaid_text
    assert "证据" in mermaid_text


def test_export_mermaid_escapes_quotes_square_brackets_ampersands_and_newlines(tmp_path):
    store.open_case(tmp_path, "Escapes", "Readable artifacts", case_id="escapes")
    node = store.add_node(tmp_path, "escapes", "evidence", 'Needs [escaping] & "quotes"\nnext line', source="file")

    result = exports.export_mermaid(tmp_path, "escapes")

    text = Path(result["path"]).read_text(encoding="utf-8")
    assert node["id"] in text
    assert "Needs &#91;escaping&#93; &amp; &quot;quotes&quot;<br/>next line" in text


def test_export_mermaid_escapes_edge_labels(tmp_path):
    build_export_case(tmp_path)
    case = store.load_case(tmp_path, "export-case")
    case["edges"][1]["type"] = 'supports & "quoted" [label]\ncontinued'
    store.save_case(tmp_path, case)

    result = exports.export_mermaid(tmp_path, "export-case")

    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "-- supports &amp; &quot;quoted&quot; &#91;label&#93;<br/>continued -->" in text
    assert '-- supports & "quoted" [label]\ncontinued -->' not in text


def test_export_markdown_normalizes_multiline_list_items(tmp_path):
    store.open_case(tmp_path, "Markdown Lines", "Readable artifacts", case_id="markdown-lines")
    observation = store.add_node(tmp_path, "markdown-lines", "observation", "Initial\nsymptom", source="user")
    evidence = store.add_node(tmp_path, "markdown-lines", "evidence", "Verified\nlog line", source="file")
    store.add_edge(
        tmp_path,
        "markdown-lines",
        observation["id"],
        evidence["id"],
        "supports",
        rationale="Log line\nmatches symptom",
    )

    result = exports.export_markdown(tmp_path, "markdown-lines")

    text = Path(result["path"]).read_text(encoding="utf-8")
    bullet_lines = [line for line in text.splitlines() if line.startswith("- ")]
    assert "- Verified log line (source: file)" in bullet_lines
    assert "- Initial symptom -- supports --> Verified log line (Log line matches symptom)" in bullet_lines
    assert "Verified\nlog line" not in text
    assert "Log line\nmatches symptom" not in text


def test_export_mermaid_uses_canonical_edge_endpoints_with_traversal_metadata(tmp_path):
    observation, evidence, hypothesis = build_export_case(tmp_path)
    case = store.load_case(tmp_path, "export-case")
    case["edges"][0].update(
        {
            "traversal_from_id": hypothesis["id"],
            "traversal_to_id": observation["id"],
            "reversed": True,
        }
    )
    store.save_case(tmp_path, case)

    result = exports.export_mermaid(tmp_path, "export-case")

    text = Path(result["path"]).read_text(encoding="utf-8")
    assert f'{observation["id"]} -- derives --> {evidence["id"]}' in text
    assert "traversal_from_id" not in text
    assert "traversal_to_id" not in text
    assert "reversed" not in text


def test_exports_propagate_missing_case_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing-case"):
        exports.export_markdown(tmp_path, "missing-case")

    with pytest.raises(FileNotFoundError, match="missing-case"):
        exports.export_mermaid(tmp_path, "missing-case")
