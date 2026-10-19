from repoclosure.evaluation import (
    METRIC_FNS,
    average_precision,
    bootstrap_ci,
    compute_metrics,
    ndcg_at_k,
    paired_bootstrap,
    recall_at_k,
    reciprocal_rank,
    summarize,
)


def test_recall_and_hit():
    assert recall_at_k(["a", "b"], {"b"}, 1) == 0.0
    assert recall_at_k(["a", "b"], {"b"}, 2) == 1.0
    assert recall_at_k(["a"], {"b"}, 5) == 0.0
    assert recall_at_k(["a"], set(), 5) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5
    assert reciprocal_rank(["a"], {"z"}) == 0.0


def test_ndcg_perfect_ranking():
    assert abs(ndcg_at_k(["a", "b"], {"a", "b"}, 10) - 1.0) < 1e-9
    assert ndcg_at_k(["x", "a"], {"a"}, 10) < 1.0


def test_average_precision():
    assert average_precision(["a", "b"], {"a", "b"}) == 1.0
    assert abs(average_precision(["a", "x", "b"], {"a", "b"}) - (1.0 + 2 / 3) / 2) < 1e-9


def test_compute_metrics_has_all_keys():
    m = compute_metrics(["a"], {"a"})
    assert set(m) == set(METRIC_FNS)


def test_summarize_and_bootstrap():
    rows = [{"recall@10": 1.0}, {"recall@10": 0.0}, {"recall@10": 1.0}]
    s = summarize(rows)
    assert s.n == 3 and abs(s.means["recall@10"] - 2 / 3) < 1e-3
    mean, lo, hi = bootstrap_ci([1.0, 0.0, 1.0, 1.0], n_boot=500)
    assert lo <= mean <= hi


def test_paired_bootstrap_detects_difference():
    a = [1.0] * 30
    b = [0.0] * 30
    out = paired_bootstrap(a, b, n_boot=1000)
    assert out["mean_diff"] == 1.0
    assert out["p"] < 0.05


def test_empty_inputs_are_safe():
    assert summarize([]).n == 0
    assert bootstrap_ci([]) == (0.0, 0.0, 0.0)
    assert paired_bootstrap([], [])["n"] == 0
