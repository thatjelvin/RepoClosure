# Experiment Matrix

One row per experiment. Raw outputs go to `results/<run_id>/`; never overwritten in place.
Status legend: TODO / RUNNING / DONE / FAILED / BLOCKED.

Environment shorthand: `LOCAL` = Celeron N4020, 2c/2t, 7.8 GB, CPU-only, Win11, Py3.13.7;
`KAGGLE` = Kaggle notebook (accelerator TBD, requires credentials — currently BLOCKED).

| ID | RQ | Method / config | Dataset | Repos | Queries | Embed model | Seed | Env | Status | Outputs |
|---|---|---|---|---|---|---|---|---|---|---|
| E00 | sanity | uniform-random lower bound | benchmark-v1 | small-Python | n | none | 42 | LOCAL | TODO | results/E00 |
| E01 | H1 | BM25 (lexical) | benchmark-v1 | small-Python | n | none | 42 | LOCAL | TODO | results/E01 |
| E02 | H1 | dense (semantic) | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E02 |
| E03 | H1 | hybrid RRF (lexical+dense) | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E03 |
| E04 | H1/H2 | graph-guided hybrid (proposed) | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E04 |
| E05 | H2 | ablation: graph signals off | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E05 |
| E06 | H3 | ablation: expansion depth 1/2/3 | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E06 |
| E07 | H3 | ablation: expansion budget | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E07 |
| E08 | H3 | ablation: edge types (calls-only vs typed) | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E08 |
| E09 | resource | indexing/embedding/query latency, memory, index size | benchmark-v1 | small-Python | n | MiniLM-L6-v2 | 42 | LOCAL | TODO | results/E09 |
| E10 | extra | path/filename search | benchmark-v1 | small-Python | n | none | 42 | LOCAL | TODO | results/E10 |
| E11 | H1/H2 | official 129-task replication | gemma4-agent-paper | official-4 | 129 | MiniLM-L6-v2 | 42 | KAGGLE | BLOCKED (creds) | notebooks/ |

## Notes
- `benchmark-v1` = curated SWE-bench-Lite subset; exact instance IDs recorded in
  `benchmarks/benchmark_v1.manifest.json`.
- All methods share the **same candidate universe** (same indexed entities) for fairness.
- Primary metrics fixed before final evaluation: file Recall@10 and Closure-Recall@10.
- Each run writes: `config.json`, `raw_predictions.jsonl`, `metrics.json`, `summary.csv`,
  `env.json`, `stdout.log`.
