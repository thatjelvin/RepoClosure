from repoclosure.fusion import minmax, ranked_ids, reciprocal_rank_fusion


def test_ranked_ids_deterministic_tiebreak():
    scores = {"b": 1.0, "a": 1.0, "c": 0.5}
    assert ranked_ids(scores) == ["a", "b", "c"]


def test_rrf_prefers_agreement():
    a = ["x", "y", "z"]
    b = ["x", "z", "y"]
    fused = reciprocal_rank_fusion([a, b], k=60)
    assert max(fused, key=fused.get) == "x"


def test_rrf_weights():
    a = ["x", "y"]
    b = ["y", "x"]
    fused = reciprocal_rank_fusion([a, b], weights=[1.0, 0.0])
    assert ranked_ids(fused)[0] == "x"


def test_minmax_bounds():
    assert minmax({}) == {}
    assert minmax({"a": 5, "b": 5}) == {"a": 0.0, "b": 0.0}
    out = minmax({"a": 0, "b": 10})
    assert out["a"] == 0.0 and out["b"] == 1.0
