from repoclosure.config import Config
from repoclosure.expansion import explain, expand_from_seeds
from repoclosure.graph import build_graph
from repoclosure.parsing import parse_repository


def _cfg():
    c = Config()
    c.retrieval.expansion_depth = 2
    c.retrieval.expansion_budget = 4
    c.retrieval.expansion_edge_types = ("calls", "imports", "contains", "references")
    return c


def test_expand_respects_budget(synthetic_repo):
    g = build_graph(parse_repository(synthetic_repo))
    res = expand_from_seeds(g, ["module:pkg/core.py"], _cfg().retrieval)
    assert len(res.records) <= 4
    assert all(0.0 <= v <= 1.0 for v in res.normalized.values())


def test_expansion_disabled_returns_empty(synthetic_repo):
    g = build_graph(parse_repository(synthetic_repo))
    cfg = _cfg()
    cfg.retrieval.expansion_enabled = False
    res = expand_from_seeds(g, ["module:pkg/core.py"], cfg.retrieval)
    assert res.records == [] and res.scores == {}


def test_empty_seeds_returns_empty(synthetic_repo):
    g = build_graph(parse_repository(synthetic_repo))
    res = expand_from_seeds(g, [], _cfg().retrieval)
    assert res.records == []


def test_explain_produces_reason(synthetic_repo):
    g = build_graph(parse_repository(synthetic_repo))
    res = expand_from_seeds(g, ["module:pkg/core.py"], _cfg().retrieval)
    if res.records:
        node = res.records[0].node
        reasons = explain(res.records, node)
        assert reasons and reasons[0]["seed"]
        assert reasons[0]["confidence"] >= 0.0


def test_deterministic_expansion(synthetic_repo):
    g1 = build_graph(parse_repository(synthetic_repo))
    g2 = build_graph(parse_repository(synthetic_repo))
    r1 = expand_from_seeds(g1, ["module:pkg/core.py"], _cfg().retrieval)
    r2 = expand_from_seeds(g2, ["module:pkg/core.py"], _cfg().retrieval)
    assert [r.node for r in r1.records] == [r.node for r in r2.records]
