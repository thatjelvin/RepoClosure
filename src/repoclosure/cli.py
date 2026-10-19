"""Command-line interface: ``repoclosure index`` and ``repoclosure search``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .indexing import METHODS, RepositoryIndex


def _index(args: argparse.Namespace) -> int:
    cfg = load_config(args.config) if args.config else None
    idx = RepositoryIndex(args.repo, cfg).build(cache_dir=args.cache_dir)
    stats = idx.build_stats
    if args.graph_out and idx.graph is not None:
        Path(args.graph_out).parent.mkdir(parents=True, exist_ok=True)
        idx.graph.to_json(args.graph_out)
        stats["graph_written_to"] = str(args.graph_out)
    if idx.parsed and idx.parsed.errors:
        stats["parse_errors"] = [f"{e.file}: {e.error_type}: {e.message}"
                                 for e in idx.parsed.errors[:20]]
    print(json.dumps(stats, indent=2))
    return 0


def _search(args: argparse.Namespace) -> int:
    cfg = load_config(args.config) if args.config else None
    idx = RepositoryIndex(args.repo, cfg).build(cache_dir=args.cache_dir)
    result = idx.search(args.query, method=args.method, top_k=args.top_k,
                        granularity=args.granularity)
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="repoclosure",
                                description="Graph-guided repository code retrieval.")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("index", help="build the repository index and print statistics")
    pi.add_argument("repo", help="path to the repository")
    pi.add_argument("--config", default=None, help="path to a JSON/YAML config")
    pi.add_argument("--cache-dir", default=None, help="directory for the embedding cache")
    pi.add_argument("--graph-out", default=None, help="write the code graph to this JSON path")
    pi.set_defaults(func=_index)

    ps = sub.add_parser("search", help="run a retrieval query")
    ps.add_argument("repo", help="path to the repository")
    ps.add_argument("--query", required=True)
    ps.add_argument("--method", default="hybrid", choices=list(METHODS))
    ps.add_argument("--top-k", type=int, default=10)
    ps.add_argument("--granularity", default=None, choices=["file", "symbol"])
    ps.add_argument("--config", default=None)
    ps.add_argument("--cache-dir", default=None)
    ps.set_defaults(func=_search)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
