"""Run the RepoClosure retrieval benchmark and persist raw + aggregated results.

Designed for a low-memory CPU machine (2 cores / 8 GB) as well as a normal CI box:

* ``--instance-id`` runs **one** benchmark instance and exits. The parent shell drives
  one process per instance so memory is fully reclaimed between repos (an in-process
  loop was observed to degrade into swap thrash on an 8 GB machine).
* ``--aggregate-only`` reads the per-instance raw files and writes the aggregate
  artefacts. As a result a long run is resumable: rerun only the missing instances.

Layout::

    results/<run_id>/
        config.json  env.json  benchmark.manifest
        raw/<instance_id>.jsonl      6 rows (one per method)
        metrics.json  summary.csv  per_repo.csv  resource_stats.csv
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from repoclosure.config import load_config
from repoclosure.evaluation import (
    bootstrap_ci,
    compute_metrics,
    paired_bootstrap,
    recall_at_k,
    summarize,
    wilcoxon,
)
from repoclosure.indexing import RepositoryIndex

ROOT = Path(__file__).resolve().parents[1]
METHODS = ["random", "lexical", "semantic", "hybrid", "graph_hybrid", "path"]
METRIC_KEYS = ("recall@1", "recall@5", "recall@10", "mrr", "ndcg@10")


def random_ranking(entity_ids: list[str], query: str) -> list[str]:
    """Deterministic pseudo-random ranking used as a lower-bound control."""
    return sorted(entity_ids, key=lambda eid: hashlib.md5(f"{query}|{eid}".encode()).hexdigest())


def env_info() -> dict:
    info = {"python": sys.version, "platform": platform.platform(),
            "processor": platform.processor(), "machine": platform.machine()}
    for mod in ("numpy", "networkx", "rank_bm25", "torch", "transformers",
                "sentence_transformers", "scipy"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "?")
        except Exception:
            info[mod] = None
    return info


def closure_metrics(ranked_files: list[str], closure_files: list[str]) -> dict[str, float]:
    cset = set(closure_files)
    if not cset:
        return {"closure_recall@1": 0.0, "closure_recall@5": 0.0,
                "closure_recall@10": 0.0, "closure_hit@10": 0.0}
    out = {f"closure_recall@{k}": recall_at_k(ranked_files, cset, k) for k in (1, 5, 10)}
    out["closure_hit@10"] = 1.0 if set(ranked_files[:10]) & cset else 0.0
    return out


def setup_run(out_dir: Path, args) -> None:
    cfg = load_config(args.config)
    cfg.retrieval.top_k = args.top_k
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
        cfg.to_json(out_dir / "config.json")
        (out_dir / "env.json").write_text(json.dumps(env_info(), indent=2), encoding="utf-8")
        (out_dir / "benchmark.manifest").write_text(
            Path(str(args.benchmark).replace(".json", ".manifest.json")).read_text(encoding="utf-8"),
            encoding="utf-8")
    (out_dir / "raw").mkdir(exist_ok=True)


def run_instance(entry: dict, args, out_dir: Path) -> None:
    cfg = load_config(args.config)
    cfg.retrieval.top_k = args.top_k

    iid = entry["instance_id"]
    dest = out_dir / "raw" / f"{iid}.jsonl"
    if dest.exists() and dest.stat().st_size > 0:
        print(f"{iid}: already done, skipping")
        return

    idx = RepositoryIndex(entry["path"], cfg).build(cache_dir=args.cache_dir)
    st = idx.build_stats
    resource = {
        "instance_id": iid, "repo": entry["repo"],
        "num_entities": st["num_entities"], "num_files": st["num_files"],
        "index_seconds": st["index_seconds"], "graph_seconds": st["graph_seconds"],
        "num_graph_nodes": st["graph"]["num_nodes"],
        "num_graph_edges": st["graph"]["num_edges"],
    }

    rows = []
    for method in args.methods:
        t0 = time.perf_counter()
        if method == "random":
            ranked_files = random_ranking(
                [e.file for e in idx.entities.values()], entry["problem_statement"])
            ranked_symbols = random_ranking(
                [e.id for e in idx.entities.values() if e.kind in ("class", "function", "method")],
                entry["problem_statement"])
        else:
            fres = idx.search(entry["problem_statement"], method=method, top_k=args.top_k,
                              granularity="file")
            ranked_files = [i.file for i in fres.items]
            sres = idx.search(entry["problem_statement"], method=method, top_k=args.top_k,
                              granularity="symbol")
            ranked_symbols = [i.id for i in sres.items]
        latency_ms = (time.perf_counter() - t0) * 1000.0

        rows.append({
            "instance_id": iid, "repo": entry["repo"], "method": method,
            "file_ranking": ranked_files, "symbol_ranking": ranked_symbols,
            "num_gold_files": len(entry["gold_files"]),
            "num_gold_symbols": len(entry["gold_symbols"]),
            "num_closure_files": len(entry["closure_files"]),
            "latency_ms": round(latency_ms, 3),
            "file_metrics": compute_metrics(ranked_files, set(entry["gold_files"])),
            "symbol_metrics": compute_metrics(ranked_symbols, set(entry["gold_symbols"])),
            "closure_metrics": closure_metrics(ranked_files, entry["closure_files"]),
            "resource": resource,
        })

    tmp = dest.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    tmp.replace(dest)
    print(f"{iid}: {st['num_entities']} entities, index {st['index_seconds']}s", flush=True)

    del idx
    gc.collect()


def aggregate(args, out_dir: Path) -> dict:
    rows = []
    for f in sorted((out_dir / "raw").glob("*.jsonl")):
        rows.extend(json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line)
    if not rows:
        raise SystemExit("no raw predictions found")

    def collect(method: str, family: str, metric: str) -> list[float]:
        return [r[family][metric] for r in rows if r["method"] == method]

    cfg = load_config(args.config)
    cfg.retrieval.top_k = args.top_k
    methods = [m for m in args.methods if any(r["method"] == m for r in rows)]
    metrics: dict = {"run_id": args.run_id, "config": cfg.to_dict(),
                     "n_instances": len({r["instance_id"] for r in rows}),
                     "n_rows": len(rows), "methods": {}}
    for method in methods:
        file_rows = [r["file_metrics"] for r in rows if r["method"] == method]
        sym_rows = [r["symbol_metrics"] for r in rows if r["method"] == method]
        clo_rows = [r["closure_metrics"] for r in rows if r["method"] == method]
        cis = {}
        for name in METRIC_KEYS:
            mean, lo, hi = bootstrap_ci(collect(method, "file_metrics", name))
            cis[f"file_{name}"] = {"mean": round(mean, 4), "lo": round(lo, 4), "hi": round(hi, 4)}
        for name in ("closure_recall@5", "closure_recall@10"):
            mean, lo, hi = bootstrap_ci(collect(method, "closure_metrics", name))
            cis[name] = {"mean": round(mean, 4), "lo": round(lo, 4), "hi": round(hi, 4)}
        lat = [r["latency_ms"] for r in rows if r["method"] == method]
        metrics["methods"][method] = {
            "file": summarize(file_rows).to_dict(),
            "symbol": summarize(sym_rows).to_dict(),
            "closure": summarize(clo_rows).to_dict(),
            "latency_ms_median": round(statistics.median(lat), 3) if lat else 0.0,
            "bootstrap_ci": cis,
        }

    comparisons = {}
    base = "hybrid"
    for other in ("graph_hybrid", "lexical", "semantic"):
        if base not in methods or other not in methods:
            continue
        for family, metric in (("file_metrics", "recall@10"), ("file_metrics", "mrr"),
                               ("closure_metrics", "closure_recall@10"),
                               ("symbol_metrics", "recall@10")):
            a = collect(other, family, metric)
            b = collect(base, family, metric)
            pb = paired_bootstrap(a, b)
            w = wilcoxon(a, b)
            comparisons[f"{other}_vs_{base}::{family}.{metric}"] = {
                **pb, **({"wilcoxon_p": w.get("p")} if w else {})}
    metrics["paired_comparisons"] = comparisons

    # resources come from the per-instance resource block (deduped)
    res = {r["instance_id"]: r["resource"] for r in rows}
    metrics["resources"] = {
        "instances": len(res),
        "index_seconds_mean": round(statistics.mean(v["index_seconds"] for v in res.values()), 3),
        "entities_mean": round(statistics.mean(v["num_entities"] for v in res.values()), 1),
        "files_mean": round(statistics.mean(v["num_files"] for v in res.values()), 1),
        "graph_nodes_mean": round(statistics.mean(v["num_graph_nodes"] for v in res.values()), 1),
        "graph_edges_mean": round(statistics.mean(v["num_graph_edges"] for v in res.values()), 1),
    }

    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    with (out_dir / "resource_stats.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(next(iter(res.values())).keys()))
        w.writeheader(); w.writerows(res.values())

    fields = ["method", "file_recall@1", "file_recall@5", "file_recall@10", "file_mrr",
              "file_ndcg@10", "symbol_recall@10", "closure_recall@5", "closure_recall@10",
              "latency_ms_median"]
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(fields)
        for method, ms in metrics["methods"].items():
            fm, sm, cm = ms["file"]["means"], ms["symbol"]["means"], ms["closure"]["means"]
            w.writerow([method, fm.get("recall@1"), fm.get("recall@5"), fm.get("recall@10"),
                        fm.get("mrr"), fm.get("ndcg@10"), sm.get("recall@10"),
                        cm.get("closure_recall@5"), cm.get("closure_recall@10"),
                        ms["latency_ms_median"]])

    repos = sorted({r["repo"] for r in rows})
    with (out_dir / "per_repo.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["method", "repo", "n", "file_recall@10", "file_mrr",
                                        "closure_recall@10"])
        for method in methods:
            for repo in repos:
                sub = [r for r in rows if r["method"] == method and r["repo"] == repo]
                if sub:
                    w.writerow([method, repo, len(sub),
                                round(statistics.mean(r["file_metrics"]["recall@10"] for r in sub), 4),
                                round(statistics.mean(r["file_metrics"]["mrr"] for r in sub), 4),
                                round(statistics.mean(r["closure_metrics"]["closure_recall@10"] for r in sub), 4)])
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=str(ROOT / "benchmarks" / "benchmark_v1.json"))
    ap.add_argument("--config", default=str(ROOT / "configs" / "default.json"))
    ap.add_argument("--methods", nargs="*", default=METHODS)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--cache-dir", default=str(ROOT / "results" / ".cache" / "embeddings"))
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--instance-id", default=None)
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()

    out_dir = ROOT / "results" / args.run_id
    setup_run(out_dir, args)
    bench = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    instances = bench["instances"][: args.limit] if args.limit else bench["instances"]

    if args.instance_id:
        entry = next((e for e in instances if e["instance_id"] == args.instance_id), None)
        if entry is None:
            print(f"unknown instance {args.instance_id}", file=sys.stderr)
            return 2
        run_instance(entry, args, out_dir)
        return 0

    if args.aggregate_only:
        metrics = aggregate(args, out_dir)
    else:
        for entry in instances:
            run_instance(entry, args, out_dir)
        metrics = aggregate(args, out_dir)

    print(f"\nwrote results to {out_dir}")
    for method, ms in metrics["methods"].items():
        fm, cm = ms["file"]["means"], ms["closure"]["means"]
        print(f"  {method:14s} fileR@10={fm.get('recall@10')} MRR={fm.get('mrr')} "
              f"closureR@10={cm.get('closure_recall@10')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
