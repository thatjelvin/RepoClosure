"""Repository index: ties parsing, graph construction and retrieval together."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import Config, RetrievalConfig
from .expansion import explain, expand_from_seeds
from .fusion import minmax, ranked_ids, reciprocal_rank_fusion
from .graph import CodeGraph, build_graph
from .parsing import Entity, ParsedRepository, parse_repository
from .retrieval import BM25Retriever, DenseRetriever, PathRetriever

SYMBOL_KINDS = {"class", "function", "method"}
ALL_KINDS = {"file", "module", "class", "function", "method"}

METHODS = ("lexical", "semantic", "path", "hybrid", "graph_hybrid")


@dataclass
class ResultItem:
    id: str
    kind: str
    name: str
    file: str
    start_line: int
    end_line: int
    rank: int
    score: float
    scores: dict[str, float] = field(default_factory=dict)
    explanation: list[dict] = field(default_factory=list)
    contributing: list[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    query: str
    method: str
    granularity: str
    items: list[ResultItem]
    warnings: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "method": self.method,
            "granularity": self.granularity,
            "warnings": self.warnings,
            "config": self.config,
            "results": [asdict(i) for i in self.items],
        }


class RepositoryIndex:
    """A searchable representation of one repository snapshot."""

    def __init__(self, root: str | Path, config: Config | None = None):
        self.root = Path(root)
        self.config = config or Config()
        self.parsed: ParsedRepository | None = None
        self.graph: CodeGraph | None = None
        self.entities: dict[str, Entity] = {}
        self._bm25: BM25Retriever | None = None
        self._dense: DenseRetriever | None = None
        self._path: PathRetriever | None = None
        self._cache: dict[str, Any] = {}
        self.build_stats: dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    def build(self, cache_dir: str | Path | None = None) -> "RepositoryIndex":
        t0 = time.perf_counter()
        self.parsed = parse_repository(self.root, self.config.parse)
        t_parse = time.perf_counter() - t0

        t0 = time.perf_counter()
        self.graph = build_graph(self.parsed, self.config.graph)
        self.entities = self.parsed.entities
        t_graph = time.perf_counter() - t0

        t0 = time.perf_counter()
        bm25 = BM25Retriever(self.config.retrieval).fit(self.entities.values())
        path = PathRetriever(self.config.retrieval).fit(self.entities.values())
        dense = DenseRetriever(self.config.retrieval)
        dense.set_cache(self._load_cache(cache_dir))
        dense.fit(self.entities.values())
        self._bm25, self._dense, self._path = bm25, dense, path
        if cache_dir is not None:
            self._save_cache(cache_dir)
        t_index = time.perf_counter() - t0

        self.build_stats = {
            "parse_seconds": round(t_parse, 4),
            "graph_seconds": round(t_graph, 4),
            "index_seconds": round(t_index, 4),
            "total_seconds": round(t_parse + t_graph + t_index, 4),
            "num_entities": len(self.entities),
            "num_files": len(self.parsed.module_files),
            "num_parse_errors": len(self.parsed.errors),
            "graph": self.graph.stats(),
        }
        return self

    # ------------------------------------------------------------------ #
    def _load_cache(self, cache_dir: str | Path | None):
        if cache_dir is None:
            return None
        vectors_path = Path(cache_dir) / "embedding_cache.npz"
        keys_path = Path(cache_dir) / "embedding_cache.keys.json"
        if not vectors_path.exists() or not keys_path.exists():
            return None
        import numpy as np
        vectors = np.load(vectors_path)["vectors"]
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
        if len(keys) != len(vectors):
            return None
        return {k: vectors[i] for i, k in enumerate(keys)}

    def _save_cache(self, cache_dir: str | Path) -> None:
        cache = self._dense.get_cache() if self._dense else None
        if not cache:
            return
        import numpy as np
        keys = list(cache.keys())
        vectors = np.stack([np.asarray(cache[k], dtype="float32") for k in keys])
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        np.savez_compressed(Path(cache_dir) / "embedding_cache.npz", vectors=vectors)
        (Path(cache_dir) / "embedding_cache.keys.json").write_text(
            json.dumps(keys), encoding="utf-8")

    # ------------------------------------------------------------------ #
    def _entity_rankings(self, query: str) -> dict[str, dict[str, float]]:
        assert self._bm25 and self._dense and self._path
        return {
            "lexical": self._bm25.score(query),
            "semantic": self._dense.score(query),
            "path": self._path.score(query),
        }

    def _entity_scores(self, query: str, method: str):
        """Return (entity_scores, audit_records, extra) for one method."""
        raw = self._entity_rankings(query)
        if method in raw:
            return raw[method], [], {}

        lex_ids = ranked_ids(raw["lexical"], self.config.retrieval.rrf_depth)
        sem_ids = ranked_ids(raw["semantic"], self.config.retrieval.rrf_depth)
        rrf = reciprocal_rank_fusion([lex_ids, sem_ids], k=self.config.retrieval.rrf_k)

        if method == "hybrid":
            return rrf, [], {}

        if method == "graph_hybrid":
            groundable = {e.id for e in self.entities.values() if e.kind in ALL_KINDS}
            seeds = [s for s in ranked_ids(rrf, self.config.retrieval.expansion_seed_k) if s in (self.graph.graph if self.graph else {})]
            exp = expand_from_seeds(
                self.graph, seeds, self.config.retrieval,
                exclude=tuple(),  # seeds are already in the base ranking
            )
            base_n = minmax({k: v for k, v in rrf.items() if k in groundable})
            w = self.config.retrieval.expansion_weight
            final: dict[str, float] = {}
            for eid in set(base_n) | set(exp.normalized):
                final[eid] = (1 - w) * base_n.get(eid, 0.0) + w * exp.normalized.get(eid, 0.0)
            return final, exp.records, {"seeds": seeds, "rrf": rrf}

        raise ValueError(f"unknown method: {method} (expected one of {METHODS})")

    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str,
        method: str = "hybrid",
        top_k: int | None = None,
        granularity: str | None = None,
    ) -> RetrievalResult:
        if method not in METHODS:
            raise ValueError(f"unknown method: {method} (expected one of {METHODS})")
        top_k = top_k or self.config.retrieval.top_k
        granularity = granularity or self.config.retrieval.granularity
        warnings: list[str] = []
        if not query or not query.strip():
            warnings.append("empty query")
            return RetrievalResult(query, method, granularity, [], warnings, self._cfg_dict())

        scores, records, extra = self._entity_scores(query, method)
        # restrict to symbol kinds for symbol granularity; files/modules only for file granularity
        allowed = SYMBOL_KINDS if granularity == "symbol" else ALL_KINDS
        filtered = {k: v for k, v in scores.items() if k in self.entities and self.entities[k].kind in allowed}

        items = self._aggregate(filtered, granularity, top_k, records, extra, query)
        return RetrievalResult(query, method, granularity, items, warnings, self._cfg_dict())

    def _cfg_dict(self) -> dict[str, Any]:
        r = self.config.retrieval
        return {
            "top_k": r.top_k, "bm25_k1": r.bm25_k1, "bm25_b": r.bm25_b,
            "rrf_k": r.rrf_k, "embed_model": r.embed_model,
            "expansion_enabled": r.expansion_enabled, "expansion_depth": r.expansion_depth,
            "expansion_budget": r.expansion_budget, "expansion_weight": r.expansion_weight,
            "expansion_edge_types": list(r.expansion_edge_types),
            "expansion_min_confidence": r.expansion_min_confidence,
        }

    # ------------------------------------------------------------------ #
    def _aggregate(
        self,
        scores: dict[str, float],
        granularity: str,
        top_k: int,
        records,
        extra: dict,
        query: str,
    ) -> list[ResultItem]:
        raw = self._entity_rankings(query)
        # order entities
        ordered = ranked_ids(scores)
        if granularity == "symbol":
            chosen = ordered[:top_k]
        else:
            best_per_file: dict[str, str] = {}
            for eid in ordered:  # ordered by score desc; first hit is the file's best
                f = self.entities[eid].file
                best_per_file.setdefault(f, eid)
            # rank files by their best entity's score
            file_order = sorted(
                best_per_file.items(),
                key=lambda kv: (-scores.get(kv[1], 0.0), kv[0]),
            )
            chosen = [eid for _, eid in file_order[:top_k]]

        items: list[ResultItem] = []
        for rank, eid in enumerate(chosen, start=1):
            ent = self.entities[eid]
            # contributing entities in the same file (for file granularity)
            contributing: list[str] = []
            if granularity == "file":
                same = [e for e in ordered if self.entities[e].file == ent.file]
                contributing = same[:5]
            items.append(ResultItem(
                id=ent.id, kind=ent.kind, name=ent.name, file=ent.file,
                start_line=ent.start_line, end_line=ent.end_line,
                rank=rank, score=round(float(scores.get(eid, 0.0)), 6),
                scores={
                    "lexical": round(float(raw["lexical"].get(eid, 0.0)), 6),
                    "semantic": round(float(raw["semantic"].get(eid, 0.0)), 6),
                    "path": round(float(raw["path"].get(eid, 0.0)), 6),
                    "fused": round(float(extra.get("rrf", {}).get(eid, scores.get(eid, 0.0))), 6),
                },
                explanation=explain(records, eid) if records else [],
                contributing=contributing,
            ))
        return items


def build_index(root: str | Path, config: Config | None = None,
                cache_dir: str | Path | None = None) -> RepositoryIndex:
    return RepositoryIndex(root, config).build(cache_dir=cache_dir)
