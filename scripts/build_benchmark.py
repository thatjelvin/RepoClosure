"""Build the RepoClosure benchmark: file-, symbol- and closure-level ground truth.

Ground truth is derived from three *documented* sources; nothing is manually verified:

1. ``gold_files`` — files modified by the SWE-bench gold ``patch``. A patch-derived
   **proxy** for relevance (necessary edits, not necessarily all files an agent needs).
2. ``gold_symbols`` — symbols whose source span intersects the changed new-file lines.
   A finer-grained **proxy**.
3. ``closure_files`` — for each gold symbol, entities reachable within ``closure_depth``
   hops in RepoClosure's own typed graph (all edge types), mapped to files, excluding the
   gold files. This is a **structural proxy**: it measures whether a retriever surfaces the
   supporting context that is structurally connected to the edit. It is derived from the
   same graph the proposed method traverses, which is a known source of optimism and is
   disclosed in the paper.

Output: ``benchmarks/benchmark_v1.json`` + ``benchmarks/benchmark_v1.manifest.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from repoclosure.config import Config, GraphConfig, ParseConfig
from repoclosure.graph import build_graph
from repoclosure.parsing import parse_repository

ROOT = Path(__file__).resolve().parents[1]

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FILE = re.compile(r"^\+\+\+ [ab]/(.+)$")


def parse_patch(patch: str) -> dict[str, set[int]]:
    """Return {file_path: set_of_changed_new_line_numbers} for a unified diff."""
    changed: dict[str, set[int]] = {}
    current: str | None = None
    new_line = 0
    for line in patch.splitlines():
        m = _FILE.match(line)
        if m:
            current = m.group(1)
            changed.setdefault(current, set())
            continue
        h = _HUNK.match(line)
        if h and current is not None:
            new_line = int(h.group(1))
            continue
        if current is None:
            continue
        if line.startswith("+"):
            changed[current].add(new_line)
            new_line += 1
        elif line.startswith("-"):
            pass
        elif line.startswith(" "):
            new_line += 1
    return {k: v for k, v in changed.items() if v}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "benchmarks" / "repo_manifest.json"))
    ap.add_argument("--swe", default=str(ROOT / "data" / "swebench_lite.json"))
    ap.add_argument("--out", default=str(ROOT / "benchmarks" / "benchmark_v1.json"))
    ap.add_argument("--closure-depth", type=int, default=2)
    ap.add_argument("--closure-budget", type=int, default=60)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    swe = json.loads(Path(args.swe).read_text(encoding="utf-8"))
    by_id = {r["instance_id"]: r for r in swe["splits"]["test"] + swe["splits"]["dev"]}

    cfg = Config()
    parse_cfg: ParseConfig = cfg.parse
    graph_cfg = GraphConfig()

    entries = []
    for inst in manifest["instances"]:
        iid = inst["instance_id"]
        row = by_id.get(iid)
        if row is None:
            continue
        repo_path = Path(inst["path"])
        if not repo_path.exists():
            print(f"skip {iid}: path missing")
            continue
        patch = row.get("patch") or ""
        changed = parse_patch(patch)
        gold_files = sorted(changed.keys())
        if not gold_files:
            print(f"skip {iid}: no changed files parsed")
            continue

        parsed = parse_repository(repo_path, parse_cfg)
        graph = build_graph(parsed, graph_cfg)
        rel_files = set(parsed.module_files.values()) | {e.file for e in parsed.entities.values()}

        # --- gold symbols -------------------------------------------------
        gold_symbols: set[str] = set()
        for gf in gold_files:
            lines = changed[gf]
            for e in parsed.entities.values():
                if e.file == gf and e.kind in ("class", "function", "method"):
                    if any(e.start_line <= ln <= e.end_line for ln in lines):
                        gold_symbols.add(e.id)
        # if no symbol matched (e.g. top-level assignment change), fall back to module
        if not gold_symbols:
            for gf in gold_files:
                gold_symbols.add(f"module:{gf}")

        # --- closure ------------------------------------------------------
        seeds = [s for s in sorted(gold_symbols) if s in graph.graph]
        records = graph.expand(seeds, depth=args.closure_depth, budget=args.closure_budget,
                               edge_types=("calls", "imports", "contains", "references"),
                               min_confidence=0.30)
        closure_ids = {r.node for r in records}
        closure_files = sorted({parsed.entities[c].file for c in closure_ids
                                if c in parsed.entities} - set(gold_files))

        entries.append({
            "instance_id": iid,
            "repo": inst["repo"],
            "base_commit": inst["base_commit"],
            "path": inst["path"],
            "problem_statement": row["problem_statement"],
            "gold_files": gold_files,
            "gold_symbols": sorted(gold_symbols),
            "closure_files": closure_files,
            "closure_entities": sorted(closure_ids),
            "stats": {
                "num_entities": len(parsed.entities),
                "num_files": len(parsed.module_files),
                "num_parse_errors": len(parsed.errors),
                "num_closure_files": len(closure_files),
                "num_gold_symbols": len(gold_symbols),
            },
        })
        print(f"built {iid}: gold_files={len(gold_files)} symbols={len(gold_symbols)} closure={len(closure_files)}")

    out = Path(args.out)
    out.write_text(json.dumps({"instances": entries}, indent=1), encoding="utf-8")
    payload_hash = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest_out = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dataset": "princeton-nlp/SWE-bench_Lite (MIT)",
        "source_url": "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite",
        "num_instances": len(entries),
        "repos": sorted({e["repo"] for e in entries}),
        "closure_depth": args.closure_depth,
        "closure_budget": args.closure_budget,
        "benchmark_sha256": payload_hash,
        "label_provenance": "patch-derived (gold files/symbols) + structurally-derived (closure)",
        "labels_manually_verified": False,
    }
    Path(str(out).replace(".json", ".manifest.json")).write_text(
        json.dumps(manifest_out, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(entries)} instances)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
