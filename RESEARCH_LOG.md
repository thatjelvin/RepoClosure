# RESEARCH LOG — RepoClosure

Reverse-chronological. Every entry records a decision, discovery, dead end, or result with
enough detail to reconstruct the reasoning.

## 2026-10-19

### Environment reconnaissance
- Laptop: Celeron N4020, 2 cores, 7.8 GB RAM, no GPU, ~80 GB free, Python 3.13.7.
- `torch 2.10`, `transformers`, `networkx`, `rank_bm25`, `scikit-learn`, `pytest` pre-installed.
- No Kaggle CLI, no `~/.kaggle/kaggle.json`. Internet + HF + GitHub API reachable.
- **Consequence:** official competition data (≈21 GB, needs credentials) cannot be downloaded
  here. All executed experiments must use an open, redistributable ground-truth set.

### Competition rules verified
- Paper track is separate from the main competition; submission = a Kaggle Writeup.
- $35k total: Best Paper $15k, **Best New Resource $10k**, Best New Application $10k.
- Deadline 2026-11-12 23:59 UTC. External data permitted. Winner license Apache-2.0.
- Encouraged topics include **Code Comprehension (graph generation/parsing/embedding)**,
  **Tasks & Benchmarks**, and **Graph Reasoning**. Released graph+embedding dataset is
  "highly encouraged" but not required.
- Recorded in `docs/competition_requirements.md`. Two items left UNRESOLVED (exact five
  criteria names; word limit) — to re-verify in a logged-in browser before submission.

### Dataset reconnaissance
- Official competition data: 129 public Python tasks over fastapi/rich/requests/httpx, with
  NetworkX AST **call** graphs and node embeddings, plus `get_code_neighbors`,
  `search_similar_code`, `get_code_subgraph` tools. Requires credentials → unavailable locally.
- Community (independent) notebook reports on that data: file recall@1/@5 — TF-IDF 0.21/0.50,
  embedding 0.05/0.21, PPR 0.08/0.26, hybrid 0.14/0.42; graph reportedly calls-only with no
  module/async nodes. **Treated as prior evidence to re-test, not fact.**

### Prior-art / novelty check
- **"RepoGraph" already exists** (Ouyang et al., ICLR 2025, arXiv:2410.14684) → dropped the
  original name. Also found **LocAgent** (arXiv:2503.09089, graph-guided localization) and
  **SweRank** (arXiv:2505.07849, supervised issue-localization ranker) — both close.
- Established retrieval benchmarks exist (CoIR, RepoBench, CodeRAG-Bench, codeloc-bench,
  CORE-Bench, Agent Retrieval Bench) → a bare "benchmark" is not novel.
- **Decision:** differentiate on (i) a **context-closure** objective, (ii) a provenance- and
  confidence-annotated typed graph (adds module/async nodes + imports edges), (iii) explainable
  budgeted expansion, and (iv) a model-agnostic, dependency-light package. Provisional name
  **RepoClosure**.
- Citation verification caught one error: arXiv `2002.05202` is *GLU Variants*, not CodeBERT —
  CodeBERT is ACL Anthology `2020.findings-emnlp.139`. All other references verified via the
  arXiv API.

### Ground-truth choice
- Chose **SWE-bench-Lite** (MIT) as the open, redistributable proxy for the competition's
  task structure: real GitHub issues, pinned base commits, gold patches. Fetched via the HF
  datasets-server API → `data/swebench_lite.json` (300 test + 23 dev instances).
- Discovery: every Lite instance's gold patch touches **exactly one file** → clean single-gold
  localization; Recall@k ∈ {0,1}, MRR = 1/rank.
- Verified shallow `git fetch --depth 1 origin <sha>` works for pinned base commits.
- **Decision:** restrict executed benchmark to small, permissively licensed repos
  (requests, flask, seaborn, marshmallow, pytest, sqlfluff, pydicom, pvlib, astroid) to fit
  a 2-core CPU and disk.

### Open risks
- Statistical power (small N, few repos).
- Proxy labels (patch-derived) — mitigated by adding the closure objective and labelling
  clearly.
- Embedding speed on 2 cores — mitigated by a small model + caching.
