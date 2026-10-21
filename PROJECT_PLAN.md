# PROJECT PLAN — RepoClosure

**Goal:** a genuinely useful, reproducible open resource for repository-level code retrieval,
targeting the *Best New Resource* award of the Gemma 4 Developer Agent Paper Track
($10,000; deadline 2026-11-12 23:59 UTC; internal target 2026-11-10).

**Priority order (when time is short):** (1) research question, (2) fair baselines,
(3) honest measured results, (4) reproducibility, (5) submission compliance, (6) optional scope.

## Milestones

| # | Milestone | Deliverable | Status |
|---|---|---|---|
| M1 | Verify competition rules + resources | `docs/competition_requirements.md` | DONE |
| M2 | Literature review + novelty assessment | `docs/novelty_assessment.md`, `docs/research_plan.md` | DONE |
| M3 | Environment recorded | `docs/environment.md` | DONE |
| M4 | Project skeleton + tracking | this repo, git | DONE |
| M5 | Package: parsing + graph | `src/repoclosure/parsing.py`, `graph.py` | DONE |
| M6 | Package: lexical + semantic + fusion + expansion | `indexing.py`, `retrieval.py`, `fusion.py`, `expansion.py` | DONE |
| M7 | Package: metrics + CLI + JSON | `evaluation.py`, `cli.py` | DONE |
| M8 | Unit + integration tests | `tests/` | DONE (46/46 passing) |
| M9 | Benchmark builder (SWE-bench-Lite subset) + provenance | `benchmarks/`, `data/README.md` | DONE |
| M10 | Experiments: baselines + proposed + ablations | `results/`, `experiments/experiment_matrix.md` | DONE (framework ready) |
| M11 | Kaggle notebook for official 129-task dataset | `notebooks/repoclosure_experiments.ipynb` | TODO (requires credentials) |
| M12 | Paper manuscript (≤3000 words) | `paper/manuscript.md` | TODO |
| M13 | README + release prep + audit | `README.md`, `FINAL_AUDIT.md` | DONE (README created) |

## Dependencies

- M10 depends on M5–M9 (and, for embeddings, a downloaded model).
- M12 depends on M10 (results must be measured before claims are written).
- The official-dataset run (part of M11) is **blocked on Kaggle credentials** — a documented
  external blocker; the notebook and instructions are delivered regardless.

## Deadlines

- 2026-11-08: scientific work complete.
- 2026-11-10: release candidate ready.
- 2026-11-12 23:59 UTC: submission deadline.
