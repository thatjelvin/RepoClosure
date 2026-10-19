"""Retrieval metrics, aggregation and uncertainty estimation.

All metrics are computed per query, then aggregated. Relevance labels here are
*sets* of file (or symbol) ids; the SWE-bench-Lite gold patch yields exactly one file,
so ``recall@k`` is 0/1 per query and ``MRR`` is ``1/rank`` of the single gold item.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Callable


# --------------------------------------------------------------------------- #
# Per-query metrics
# --------------------------------------------------------------------------- #
def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def hit_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(ranked[:k]) & relevant else 0.0


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(ranked[:k]) & relevant) / k


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for i, doc in enumerate(ranked, start=1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = 0.0
    for i, doc in enumerate(ranked[:k], start=1):
        if doc in relevant:
            dcg += 1.0 / math.log2(i + 1)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(k, len(relevant)) + 1))
    return dcg / ideal if ideal > 0 else 0.0


def average_precision(ranked: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for i, doc in enumerate(ranked, start=1):
        if doc in relevant:
            hits += 1
            total += hits / i
    return total / len(relevant)


METRIC_FNS: dict[str, Callable[[list[str], set[str], int], float]] = {
    "recall@1": lambda r, rel, k: recall_at_k(r, rel, 1),
    "recall@5": lambda r, rel, k: recall_at_k(r, rel, 5),
    "recall@10": lambda r, rel, k: recall_at_k(r, rel, 10),
    "precision@10": lambda r, rel, k: precision_at_k(r, rel, 10),
    "ndcg@10": lambda r, rel, k: ndcg_at_k(r, rel, 10),
    "mrr": lambda r, rel, k: reciprocal_rank(r, rel),
    "map": lambda r, rel, k: average_precision(r, rel),
}


def compute_metrics(ranked: list[str], relevant: set[str]) -> dict[str, float]:
    return {name: fn(ranked, relevant, 10) for name, fn in METRIC_FNS.items()}


# --------------------------------------------------------------------------- #
# Aggregation + uncertainty
# --------------------------------------------------------------------------- #
@dataclass
class MetricSummary:
    n: int
    means: dict[str, float]
    stds: dict[str, float]

    def to_dict(self) -> dict:
        return {"n": self.n, "means": self.means, "stds": self.stds}


def summarize(per_query: list[dict[str, float]]) -> MetricSummary:
    if not per_query:
        return MetricSummary(0, {}, {})
    keys = sorted(per_query[0].keys())
    means = {k: mean(row.get(k, 0.0) for row in per_query) for k in keys}
    stds = {k: (pstdev([row.get(k, 0.0) for row in per_query]) if len(per_query) > 1 else 0.0) for k in keys}
    return MetricSummary(len(per_query), {k: round(v, 4) for k, v in means.items()},
                         {k: round(v, 4) for k, v in stds.items()})


def bootstrap_ci(values: list[float], n_boot: int = 10000, alpha: float = 0.05,
                 seed: int = 42) -> tuple[float, float, float]:
    """(mean, lower, upper) percentile bootstrap CI for the mean."""
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot) - 1]
    return mean(values), lo, hi


def paired_bootstrap(a: list[float], b: list[float], n_boot: int = 10000,
                     seed: int = 42) -> dict[str, float]:
    """Paired difference a-b with percentile CI and a two-sided bootstrap p-value.

    ``p`` is the fraction of resampled mean differences whose sign differs from the
    observed one, doubled (a conventional bootstrap significance approximation). This
    is reported as an approximation, not exact frequentist significance.
    """
    if len(a) != len(b) or not a:
        return {"mean_diff": 0.0, "lo": 0.0, "hi": 0.0, "p": 1.0, "n": 0}
    diffs = [x - y for x, y in zip(a, b)]
    obs = mean(diffs)
    rng = random.Random(seed)
    n = len(diffs)
    boots = []
    for _ in range(n_boot):
        boots.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot) - 1]
    if obs >= 0:
        p = 2 * sum(1 for x in boots if x <= 0) / n_boot
    else:
        p = 2 * sum(1 for x in boots if x >= 0) / n_boot
    return {"mean_diff": round(obs, 4), "lo": round(lo, 4), "hi": round(hi, 4),
            "p": round(min(1.0, p), 4), "n": n}


def wilcoxon(a: list[float], b: list[float]) -> dict[str, float]:
    """Wilcoxon signed-rank test if scipy is available; else returns empty."""
    try:
        from scipy.stats import wilcoxon as _w  # type: ignore
    except Exception:
        return {}
    diffs = [x - y for x, y in zip(a, b)]
    if all(d == 0 for d in diffs):
        return {"statistic": 0.0, "p": 1.0}
    try:
        stat, p = _w(diffs)
        return {"statistic": round(float(stat), 4), "p": round(float(p), 6)}
    except Exception:
        return {}
