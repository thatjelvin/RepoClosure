# Environment

**Recorded:** 2026-10-19

## Laptop (development + orchestration)

| Item | Value |
|---|---|
| OS | Windows (win32), PowerShell 7+ |
| CPU | Intel Celeron N4020 @ 1.10 GHz — **2 cores / 2 threads** |
| RAM | 7.82 GB |
| GPU | none (`nvidia-smi` not present) |
| Free disk | ~80.6 GB |
| Python | 3.13.7 |
| pip | 25.2 |
| git | 2.52.0.windows.1 |
| node | v22.13.1 |
| Kaggle CLI | **not installed** |
| Kaggle credentials | **not present** (`~/.kaggle/kaggle.json` absent) |
| Internet | available (PyPI, HuggingFace, GitHub API reachable) |

### Pre-installed Python packages (relevant)

| Package | Version |
|---|---|
| numpy | 2.4.3 |
| scikit-learn | 1.8.0 |
| scipy | (via scikit-learn) |
| networkx | 3.6.1 |
| rank-bm25 | 0.2.2 |
| torch | 2.10.0 (CPU) |
| transformers | 4.57.6 |
| pytest | 8.3.5 |
| pytest-asyncio | 0.25.3 |

`sentence-transformers` is **not** installed; installed on demand or the model is loaded
directly via `transformers`.

## Kaggle (experiments)

| Item | Value |
|---|---|
| Session inspection | **NOT YET INSPECTED** — requires Kaggle account access |
| Accelerator | unknown |
| Kaggle CLI/API | unavailable locally |
| Known (official) | competition data download ≈ 21 GB; dataset ships `tasks.jsonl` (129 tasks), `snapshots/`, `graphs/`, embeddings, wheels, docker specs |

**Consequence:** any result that requires the official competition dataset is **prepared but
unexecuted** in this environment, and is labelled as such everywhere. Local experiments use
open, redistributable ground truth (SWE-bench-Lite, MIT).

## Reproducibility notes

- All random seeds fixed via config (`configs/default.yaml`).
- Embedding model and revision pinned in config; first run downloads the model (needs network).
- Cold-start (model download + index build) is reported separately from warm query latency.
- Hardware above is CPU-only; results are not comparable to GPU-reported numbers elsewhere
  without this caveat.
