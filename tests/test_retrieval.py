from repoclosure.config import Config
from repoclosure.indexing import RepositoryIndex


def test_lexical_finds_auth_for_expiry_query(sample_index):
    res = sample_index.search("authentication fails with expired tokens", method="lexical", top_k=5)
    files = [i.file for i in res.items]
    assert "app/auth.py" in files


def test_semantic_hashing_runs(sample_index):
    res = sample_index.search("token expiry", method="semantic", top_k=5)
    assert res.items
    assert all(0.0 <= i.score <= 1.0 + 1e-6 for i in res.items)


def test_empty_query_is_handled(sample_index):
    res = sample_index.search("", method="hybrid")
    assert res.items == []
    assert "empty query" in res.warnings


def test_all_methods_return_ranked_files(sample_index):
    for method in ("lexical", "semantic", "path", "hybrid", "graph_hybrid"):
        res = sample_index.search("verify token signature", method=method, top_k=5)
        assert res.items, method
        ranks = [i.rank for i in res.items]
        assert ranks == list(range(1, len(res.items) + 1))


def test_symbol_granularity(sample_index):
    res = sample_index.search("expired token", method="hybrid", top_k=5, granularity="symbol")
    assert res.items
    assert all(i.kind in {"class", "function", "method"} for i in res.items)


def test_graph_hybrid_produces_explanations(sample_index):
    res = sample_index.search("expired token verify", method="graph_hybrid", top_k=8)
    # at least some items should carry a graph explanation or contributing entities
    assert any(i.explanation or i.contributing for i in res.items)


def test_unknown_method_raises(sample_index):
    import pytest
    with pytest.raises(ValueError):
        sample_index.search("x", method="nope")


def test_unknown_repo_does_not_crash(tmp_path):
    cfg = Config()
    cfg.retrieval.embed_model = "hashing"
    idx = RepositoryIndex(tmp_path, cfg).build()
    res = idx.search("anything", method="graph_hybrid")
    assert res.items == []


def test_dense_cache_is_namespaced_by_backend():
    """Vectors from different encoders must never share a cache key."""
    from repoclosure.retrieval import DenseRetriever

    cfg = Config()
    cfg.retrieval.embed_model = "hashing"
    d = DenseRetriever(cfg.retrieval)
    d.encode(["hello world"])
    keys_after = set(d.get_cache())
    assert keys_after
    assert all("|hashing|" in k for k in keys_after)

    d2 = DenseRetriever(cfg.retrieval)
    d2.set_cache(d.get_cache())
    d2.encode(["hello world"])
    assert set(d2.get_cache()) == keys_after
