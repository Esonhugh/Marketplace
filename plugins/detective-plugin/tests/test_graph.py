import pytest

from detective_mcp import graph, store


def build_case(tmp_path):
    store.open_case(tmp_path, "Graph Case", "Description", case_id="graph-case")
    observation = store.add_node(tmp_path, "graph-case", "observation", "Config changed on Monday", source="user", tags=["config"])
    evidence = store.add_node(tmp_path, "graph-case", "evidence", "Diff shows timeout changed", source="file", tags=["config", "timeout"])
    hypothesis = store.add_node(tmp_path, "graph-case", "hypothesis", "Timeout change caused regression", source="agent")
    question = store.add_node(tmp_path, "graph-case", "question", "Was traffic higher that day?", source="agent")
    store.add_edge(tmp_path, "graph-case", observation["id"], evidence["id"], "derives")
    store.add_edge(tmp_path, "graph-case", evidence["id"], hypothesis["id"], "supports")
    store.add_edge(tmp_path, "graph-case", question["id"], hypothesis["id"], "requires")
    return observation, evidence, hypothesis, question


def test_graph_overview_counts_roles_and_density(tmp_path):
    build_case(tmp_path)

    overview = graph.graph_overview(tmp_path, "graph-case")

    assert overview["case_id"] == "graph-case"
    assert overview["total_nodes"] == 4
    assert overview["total_edges"] == 3
    assert overview["by_type"]["hypothesis"] == 1
    assert overview["active_hypotheses"] == 1
    assert overview["open_questions"] == 1
    assert overview["graph_density"] == 0.75
    assert overview["edge_node_ratio"] == 0.75


def test_list_nodes_filters_by_type_status_and_tag(tmp_path):
    build_case(tmp_path)

    assert len(graph.list_nodes(tmp_path, "graph-case", node_type="evidence")) == 1
    assert len(graph.list_nodes(tmp_path, "graph-case", status="open")) == 4
    assert len(graph.list_nodes(tmp_path, "graph-case", tag="timeout")) == 1


def test_list_nodes_filters_tag_case_insensitively(tmp_path):
    build_case(tmp_path)

    matches = graph.list_nodes(tmp_path, "graph-case", tag="TIMEOUT")

    assert len(matches) == 1
    assert matches[0]["type"] == "evidence"


def test_search_nodes_matches_content_and_tags(tmp_path):
    build_case(tmp_path)

    content_matches = graph.search_nodes(tmp_path, "graph-case", query="timeout")
    tag_matches = graph.search_nodes(tmp_path, "graph-case", query="config")

    assert {node["type"] for node in content_matches} >= {"evidence", "hypothesis"}
    assert {node["type"] for node in tag_matches} >= {"observation", "evidence"}


def test_neighbors_returns_incoming_and_outgoing(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    neighbors = graph.neighbors(tmp_path, "graph-case", hypothesis["id"])

    assert {edge["from_id"] for edge in neighbors["incoming_edges"]} == {evidence["id"], question["id"]}
    assert neighbors["outgoing_edges"] == []


def test_shortest_path_directed_and_undirected(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    directed = graph.shortest_path(tmp_path, "graph-case", observation["id"], hypothesis["id"])
    reverse_directed = graph.shortest_path(tmp_path, "graph-case", hypothesis["id"], observation["id"])
    reverse_undirected = graph.shortest_path(tmp_path, "graph-case", hypothesis["id"], observation["id"], undirected=True)

    assert directed["reason"] == "found"
    assert [node["id"] for node in directed["nodes"]] == [observation["id"], evidence["id"], hypothesis["id"]]
    assert reverse_directed["reason"] == "no_path"
    assert reverse_directed["nodes"] == []
    assert [node["id"] for node in reverse_undirected["nodes"]] == [hypothesis["id"], evidence["id"], observation["id"]]


def test_shortest_path_returns_missing_endpoint_reason_for_unknown_endpoint(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    result = graph.shortest_path(tmp_path, "graph-case", observation["id"], "missing-node")

    assert result["reason"] == "missing_endpoint"
    assert result["nodes"] == []
    assert result["edges"] == []


def test_shortest_path_returns_no_path_reason_for_disconnected_valid_nodes(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)
    disconnected = store.add_node(tmp_path, "graph-case", "observation", "Unrelated fact", source="user")

    result = graph.shortest_path(tmp_path, "graph-case", hypothesis["id"], disconnected["id"])

    assert result["reason"] == "no_path"
    assert result["nodes"] == []
    assert result["edges"] == []


def test_shortest_path_normalizes_undirected_reverse_edge_steps(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    result = graph.shortest_path(tmp_path, "graph-case", hypothesis["id"], observation["id"], undirected=True)

    path_ids = [node["id"] for node in result["nodes"]]
    assert path_ids == [hypothesis["id"], evidence["id"], observation["id"]]
    assert [(edge["traversal_from_id"], edge["traversal_to_id"]) for edge in result["edges"]] == list(
        zip(path_ids, path_ids[1:])
    )
    assert all(edge["reversed"] is True for edge in result["edges"])
    assert [(edge["from_id"], edge["to_id"]) for edge in result["edges"]] == [
        (evidence["id"], hypothesis["id"]),
        (observation["id"], evidence["id"]),
    ]


def test_shortest_path_handles_cycles(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)
    store.add_edge(tmp_path, "graph-case", hypothesis["id"], observation["id"], "related_to")

    result = graph.shortest_path(tmp_path, "graph-case", observation["id"], hypothesis["id"])

    assert result["reason"] == "found"
    assert [node["id"] for node in result["nodes"]] == [observation["id"], evidence["id"], hypothesis["id"]]


def test_list_edges_filters_by_type_and_endpoints(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)

    assert len(graph.list_edges(tmp_path, "graph-case", edge_type="supports")) == 1
    assert len(graph.list_edges(tmp_path, "graph-case", from_id=question["id"])) == 1
    assert len(graph.list_edges(tmp_path, "graph-case", to_id=hypothesis["id"])) == 2


def test_get_edge_returns_existing_edge(tmp_path):
    observation, evidence, hypothesis, question = build_case(tmp_path)
    edge = graph.list_edges(tmp_path, "graph-case", edge_type="supports")[0]

    fetched = graph.get_edge(tmp_path, "graph-case", edge["id"])

    assert fetched == edge


def test_get_edge_raises_for_missing_edge(tmp_path):
    build_case(tmp_path)

    with pytest.raises(KeyError, match="Edge not found: missing-edge"):
        graph.get_edge(tmp_path, "graph-case", "missing-edge")


def test_get_node_raises_for_missing_node(tmp_path):
    build_case(tmp_path)

    with pytest.raises(KeyError, match="Node not found: missing-node"):
        graph.get_node(tmp_path, "graph-case", "missing-node")
