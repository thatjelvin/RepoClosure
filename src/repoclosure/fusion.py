"""Score fusion utilities.

Reciprocal Rank Fusion (Cormack, Clarke & Buettcher, SIGIR 2009):

    score(d) = sum_i  weight_i / (k + rank_i(d))

RRF is used because it is unsupervised, requires no score calibration, and is the
established strong default for combining heterogeneous rankers (see also the
behaviour of hybrid retrieval reported in the wider IR literature).
"""
from __future__ import annotations


def ranked_ids(scores: dict[str, float], depth: int | None = None) -> list[str]:
    """Deterministically rank ids by descending score, then ascending id."""
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    ids = [k for k, _ in ordered]
    return ids[:depth] if depth else ids


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
    weights: list[float] | None = None,
) -> dict[str, float]:
    """Fuse several ranked id lists into one score mapping."""
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights length must match rankings length")
    scores: dict[str, float] = {}
    for ranking, w in zip(rankings, weights):
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + w / (k + rank)
    return scores


def minmax(scores: dict[str, float]) -> dict[str, float]:
    """Scale scores to [0, 1]. Empty or constant input maps to zeros."""
    if not scores:
        return {}
    lo = min(scores.values())
    hi = max(scores.values())
    if hi - lo < 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}
