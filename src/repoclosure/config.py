"""Configuration objects for RepoClosure.

All tunable constants live here (or are loaded from a YAML/JSON config file), so that
experimental constants are never scattered across the codebase.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Default directories that are never part of a repository's *source*.
DEFAULT_IGNORED_DIRS = (
    ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "env", ".env",
    "build", "dist", "node_modules", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "site-packages", ".eggs", "htmlcov", ".idea", ".vscode",
    "docs/_build", ".nox", "target", ".cache",
)

# File suffixes we will attempt to parse.
DEFAULT_SOURCE_SUFFIXES = (".py",)

# Substrings that mark a path as generated / vendored / irrelevant.
DEFAULT_IGNORED_PATH_PARTS = (
    "/migrations/", "generated", "_pb2.py", ".min.js", "vendor/", "third_party/",
)


@dataclass
class ParseConfig:
    source_suffixes: tuple[str, ...] = DEFAULT_SOURCE_SUFFIXES
    ignored_dirs: tuple[str, ...] = DEFAULT_IGNORED_DIRS
    ignored_path_parts: tuple[str, ...] = DEFAULT_IGNORED_PATH_PARTS
    max_file_bytes: int = 2_000_000
    include_private: bool = True
    parse_failures_are_recorded: bool = True


@dataclass
class GraphConfig:
    # Which edge types are allowed to be *created*. All are probed by the parser;
    # this only filters construction.
    enabled_edge_types: tuple[str, ...] = (
        "contains", "imports", "calls", "references",
    )
    # Minimum confidence for an edge to be kept.
    min_confidence: float = 0.0
    # Whether to add name-heuristic call edges (low confidence).
    enable_heuristic_calls: bool = True
    heuristic_call_confidence: float = 0.30
    # Whether to include test files as retrievable entities.
    include_tests: bool = True


@dataclass
class RetrievalConfig:
    top_k: int = 10
    # BM25 parameters (Robertson & Zaragoza, 2009).
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    # Reciprocal Rank Fusion constant (Cormack et al., 2009).
    rrf_k: int = 60
    rrf_depth: int = 100
    # Dense retrieval.
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embed_batch_size: int = 32
    embed_max_chars: int = 800
    embed_seq_length: int = 256
    # Graph-guided expansion.
    expansion_enabled: bool = True
    expansion_depth: int = 1
    expansion_budget: int = 25
    expansion_edge_types: tuple[str, ...] = ("calls", "imports", "contains", "references")
    expansion_seed_k: int = 10
    expansion_weight: float = 0.30
    expansion_min_confidence: float = 0.30
    # Context granularity for the returned ranking.
    granularity: str = "file"  # "file" | "symbol"


@dataclass
class Config:
    seed: int = 42
    parse: ParseConfig = field(default_factory=ParseConfig)
    graph: GraphConfig = field(default_factory=GraphConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def _merge(dc: Any, data: dict[str, Any]) -> None:
    for key, value in data.items():
        if not hasattr(dc, key):
            continue
        current = getattr(dc, key)
        if hasattr(current, "__dataclass_fields__") and isinstance(value, dict):
            _merge(current, value)
        elif isinstance(current, tuple) and isinstance(value, list):
            setattr(dc, key, tuple(value))
        else:
            setattr(dc, key, value)


def load_config(path: str | Path | None = None) -> Config:
    cfg = Config()
    if path is None:
        return cfg
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            raise RuntimeError("PyYAML required to read YAML configs") from None
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    _merge(cfg, data)
    return cfg
