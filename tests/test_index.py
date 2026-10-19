import json

from repoclosure.indexing import RepositoryIndex


def test_build_stats_schema(sample_index):
    s = sample_index.build_stats
    for key in ("parse_seconds", "graph_seconds", "index_seconds", "total_seconds",
                "num_entities", "num_files", "num_parse_errors", "graph"):
        assert key in s
    assert s["graph"]["num_nodes"] > 0


def test_result_json_schema(sample_index):
    res = sample_index.search("token", method="graph_hybrid", top_k=3)
    payload = res.to_dict()
    assert set(payload) >= {"query", "method", "granularity", "results", "config", "warnings"}
    item = payload["results"][0]
    for key in ("id", "kind", "file", "start_line", "end_line", "rank", "score", "scores"):
        assert key in item
    assert isinstance(item["scores"], dict)


def test_embedding_cache_reuse(synthetic_repo, hashing_config, tmp_path):
    cache = tmp_path / "cache"
    a = RepositoryIndex(synthetic_repo, hashing_config).build(cache_dir=cache)
    assert (cache / "embedding_cache.npz").exists()
    b = RepositoryIndex(synthetic_repo, hashing_config).build(cache_dir=cache)
    ra = a.search("helper", method="hybrid", top_k=3)
    rb = b.search("helper", method="hybrid", top_k=3)
    assert [i.id for i in ra.items] == [i.id for i in rb.items]


def test_graph_serialization_roundtrip(synthetic_repo, hashing_config, tmp_path):
    idx = RepositoryIndex(synthetic_repo, hashing_config).build()
    out = tmp_path / "g.json"
    idx.graph.to_json(out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["stats"]["num_nodes"] == idx.graph.graph.number_of_nodes()
    # every edge references nodes present in the node list
    node_ids = {n["id"] for n in payload["nodes"]}
    for e in payload["edges"]:
        assert e["source"] in node_ids and e["target"] in node_ids


def test_empty_repository(tmp_path, hashing_config):
    idx = RepositoryIndex(tmp_path, hashing_config).build()
    assert idx.search("x", method="graph_hybrid").items == []
    assert idx.build_stats["num_entities"] == 0
