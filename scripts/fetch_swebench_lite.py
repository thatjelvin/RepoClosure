"""Fetch SWE-bench Lite (princeton-nlp/SWE-bench_Lite) via the HuggingFace
datasets-server API and cache it locally as JSON.

Provenance: SWE-bench is released by the SWE-bench authors (Jimenez et al., ICLR 2024)
under the MIT license. We only *cache* it for local experimentation and record the
source URL + retrieval date. See data/README.md.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DATASET = "princeton-nlp/SWE-bench_Lite"
BASE = "https://datasets-server.huggingface.co"
OUT = Path(__file__).resolve().parents[1] / "data" / "swebench_lite.json"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "repolenz-research"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_split(split: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page = 100
    while True:
        url = f"{BASE}/rows?dataset={DATASET}&config=default&split={split}&offset={offset}&length={page}"
        data = get_json(url)
        batch = [r["row"] for r in data.get("rows", [])]
        rows.extend(batch)
        total = data.get("num_rows_total", len(rows))
        offset += page
        if offset >= total or not batch:
            break
    return rows


def main() -> int:
    payload = {"source": f"{BASE}/rows?dataset={DATASET}", "splits": {}}
    for split in ("dev", "test"):
        try:
            rows = fetch_split(split)
            payload["splits"][split] = rows
            print(f"{split}: {len(rows)} rows", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR fetching {split}: {exc}", file=sys.stderr)
            return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
