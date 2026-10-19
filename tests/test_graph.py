from repoclosure.config import Config, GraphConfig
from repoclosure.graph import build_graph
from repoclosure.parsing import parse_repository


def _graph(repo):
    return build_graph(parse_repository(repo))


def test_structural_contains_edges(synthetic_repo):
    g = _graph(synthetic_repo)
    # file -> module, module -> function, class -> method
    assert g.graph.has_edge("file:pkg/core.py", "module:pkg/core.py")
    assert any(d["type"] == "contains" for _, _, d in g.graph.out_edges("module:pkg/core.py", data=True))


def test_import_edges_resolved(synthetic_repo):
    g = _graph(synthetic_repo)
    assert g.graph.has_edge("module:pkg/core.py", "module:pkg/util.py")
    assert g.graph["module:pkg/core.py"]["module:pkg/util.py"][0]["type"] == "imports"


def test_call_edges_and_provenance(synthetic_repo):
    g = _graph(synthetic_repo)
    calls = [(u, v, d) for u, v, d in g.graph.edges(data=True) if d["type"] == "calls"]
    assert calls, "expected at least one call edge"
    run_id = next(e.id for e in g.entities.values() if e.name == "run")
    helper_id = next(e.id for e in g.entities.values() if e.name == "helper")
    assert (run_id, helper_id) in [(u, v) for u, v, _ in calls]
    for _, _, d in calls:
        assert d["provenance"] in {"ast_call", "name_heuristic"}
        assert 0.0 < d["confidence"] <= 1.0


def test_module_and_async_nodes_present(synthetic_repo):
    g = _graph(synthetic_repo)
    stats = g.stats()
    assert stats["node_kinds"].get("async_functions", 0) == 0  # not a node kind
    assert stats["async_functions"] >= 1
    assert stats["node_kinds"].get("module", 0) >= 1


def test_neighbors_and_min_confidence(synthetic_repo):
    g = _graph(synthetic_repo)
    run_id = next(e.id for e in g.entities.values() if e.name == "run")
    nbrs = g.neighbors(run_id, edge_types=["calls"], direction="out")
    assert any(data["type"] == "calls" for _, data, _ in nbrs)
    assert g.neighbors(run_id, min_confidence=2.0) == []


def test_expand_budget_and_explanation(synthetic_repo):
    g = _graph(synthetic_repo)
    core = "module:pkg/core.py"
    records = g.expand([core], depth=3, budget=5, edge_types=["calls", "imports", "contains"])
    assert len(records) <= 5
    for r in records:
        assert r.hop >= 1
        assert r.provenance
    # serialization round-trips without error
    import json
    payload = json.loads(json.dumps({
        "nodes": g.graph.number_of_nodes(), "edges": g.graph.number_of_edges()}))
    assert payload["nodes"] > 0


def test_heuristic_calls_can_be_disabled(synthetic_repo):
    g = build_graph(parse_repository(synthetic_repo), GraphConfig(enable_heuristic_calls=False))
    assert all(d["provenance"] != "name_heuristic" for _, _, d in g.graph.edges(data=True))
