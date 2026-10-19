"""Budgeted, explainable graph-guided context expansion.

Given seed entities (from a base ranking) we traverse the code graph along a
configurable set of edge types, up to a depth and an entity budget, and produce both
a relevance score per reached entity and a human-readable *reason* for every inclusion.
The reason records the seed, the edge type, the provenance label, the confidence and
the hop distance, so a downstream agent can audit exactly why an entity was added.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import RetrievalConfig
from .fusion import minmax
from .graph import CodeGraph, ExpansionRecord


@dataclass
class ExpansionResult:
    scores: dict[str, float]          # entity id -> raw graph relevance
    normalized: dict[str, float]      # entity id -> [0,1] normalized
    records: list[ExpansionRecord]    # audit trail, one per expanded entity
    seeds: list[str]


def expand_from_seeds(
    graph: CodeGraph,
    seeds: list[str],
    config: RetrievalConfig,
    exclude: tuple[str, ...] = (),
) -> ExpansionResult:
    """Run bounded expansion and convert the audit trail into a score map."""
    if not config.expansion_enabled or not seeds:
        return ExpansionResult({}, {}, [], list(seeds))

    records = graph.expand(
        seeds=seeds,
        depth=config.expansion_depth,
        budget=config.expansion_budget,
        edge_types=config.expansion_edge_types,
        min_confidence=config.expansion_min_confidence,
        exclude=exclude,
    )

    raw: dict[str, float] = {}
    for rec in records:
        # closer hops and higher-confidence edges contribute more
        contribution = rec.confidence / max(1, rec.hop)
        raw[rec.node] = raw.get(rec.node, 0.0) + contribution
    return ExpansionResult(raw, minmax(raw), records, list(seeds))


def explain(records: list[ExpansionRecord], node: str, max_reasons: int = 3) -> list[dict]:
    """Return up to ``max_reasons`` audit entries for a single node."""
    out = []
    for rec in records:
        if rec.node != node:
            continue
        out.append({
            "seed": rec.seed,
            "edge_type": rec.edge_type,
            "provenance": rec.provenance,
            "confidence": round(rec.confidence, 3),
            "hop": rec.hop,
            "direction": rec.direction,
        })
        if len(out) >= max_reasons:
            break
    return out
