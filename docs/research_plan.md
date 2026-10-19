# Research Plan — RepoClosure

**Status:** active · **Last updated:** 2026-10-19

## 1. Problem statement

AI coding agents must retrieve the small fraction of a repository that matters for a given
natural-language issue, before they can edit it. On the Gemma 4 Developer Agent competition,
agents are handed a repository snapshot, a bug report, a pre-built call graph, and node
embeddings, and must locate and patch the fault. Independent community studies of that
released data report that **simple lexical retrieval (TF-IDF/BM25) dominates both the released
embeddings and personalized PageRank over the released graph** for localizing the edited file.
That raises a concrete question the field has not answered with a reusable artifact: **when,
if ever, do graph structure and semantics add value for repository-level code retrieval — and
on which objective?**

## 2. Research question

Can combining source-code dependency graphs, semantic embeddings, and lexical retrieval
improve the identification of *relevant code* for repository-level software-engineering tasks —
(a) the file/entity that must be edited, and (b) the *supporting* entities an agent must
understand — while remaining practical, explainable, reusable, and reproducible?

## 3. Hypotheses (to be tested, not assumed)

- **H1 (edit localization).** Graph-guided hybrid retrieval does not substantially improve
  edit-location recall over a lexical+semantic hybrid on a single-gold-file benchmark; lexical
  signal dominates (consistent with prior community observation).
- **H2 (context closure).** Graph-guided expansion *does* improve recall of the **supporting
  context closure** (callees, defining modules, imported helpers reachable from the gold
  edit) over non-graph methods, because that signal is not lexically or semantically apparent
  in the issue text.
- **H3 (conditionality).** The benefit of graph expansion depends on graph completeness
  (edge types available, presence of module/async nodes) and on expansion budget; it can harm
  ranking when budget is large or the graph is sparse.

## 4. Closest existing methods (see `novelty_assessment.md` for full table)

RepoGraph (ICLR 2025, line-level graph plug-in), LocAgent (graph-guided LLM agent),
SweRank (supervised issue-localization ranking model), CoIR / RepoBench / CodeRAG-Bench
(code retrieval benchmarks), and issue-to-edit localization harnesses. RepoClosure differs by
being (i) model-agnostic and dependency-light, (ii) explainable per-item, (iii) evaluating a
**context-closure** objective in addition to edit localization, and (iv) shipping a
reproducible harness with a graph builder that adds module/async nodes and provenance-labelled
edges absent from the released competition graphs.

## 5. Precise contribution

1. **`repoclosure` package** — parsing, typed provenance-annotated graph, BM25 lexical
   retrieval, local-embedding semantic retrieval, transparent RRF fusion, budgeted explainable
   graph expansion, retrieval metrics, and a CLI + JSON output. Python first; other languages
   pluggable.
2. **A context-closure evaluation methodology** — an automatically derived, documented metric
   that scores whether retrieval surfaces supporting entities reachable from the gold edit,
   complementing (not replacing) edit-location metrics.
3. **An open, reproducible benchmark harness** on MIT-licensed ground truth plus an adapter
   for the competition's 129-task dataset, with file- and symbol-level metrics, bootstrap CIs,
   paired tests, and full provenance.
4. **Empirical characterization** of when graph signals help or hurt, with ablations over
   edge types, expansion depth, and fusion.

## 6. Evaluation dataset

- **Primary (executed locally):** a curated subset of **SWE-bench-Lite** restricted to
  permissively licensed, small Python repositories (requests, flask, seaborn, marshmallow,
  pytest, sqlfluff, pydicom, pvlib, astroid). Each instance: `problem_statement`, pinned
  `base_commit`, gold `patch` (exactly one file in Lite), repo. Ground truth = files changed by
  the gold patch (**file-level**) and the symbols those files define that the changed hunks
  touch (**symbol-level, proxy**), plus a derived **context closure**.
- **Secondary (prepared, run on Kaggle):** the official 129-task competition set with released
  graphs/embeddings, via an adapter. Requires Kaggle credentials (not available locally).

**Ground-truth nature (honest):** patch-derived labels are a **proxy** for relevance. Changed
files are necessary but not sufficient; supporting files an agent needs may not appear in the
patch. This is precisely why we add the closure metric. Labels are **automatically derived, not
manually verified**; we say so everywhere.

## 7. Baselines (same queries, same candidate universe)

- **A. Lexical** — BM25 over file and symbol text.
- **B. Semantic** — cosine similarity with a small local embedding model.
- **C. Hybrid (no graph)** — RRF fusion of A and B.
- **P. Proposed — Graph-guided hybrid** — C + graph-derived relevance + budgeted expansion.
- **Extra:** filename/path search, and a uniform/random-of-zero lower bound for sanity.

## 8. Metrics

- **File-level:** Recall@1/@5/@10, MRR, nDCG@10 (single gold file → Recall@k ∈ {0,1}).
- **Symbol-level:** Recall@k, MRR over gold symbols.
- **Context closure:** Closure-Recall@k — fraction of gold closure entities retrieved.
- **Primary metric chosen before final test:** file-level **Recall@10** and closure recall,
  reported together because the paper's thesis is that objective choice changes the verdict.
- **Statistics:** paired bootstrap CIs (10k resamples) on per-query metric differences and a
  paired test (Wilcoxon signed-rank where appropriate); effect sizes reported; per-repo
  breakdowns; failure cases analysed.

## 9. Anticipated compute

- Laptop: 2-core Intel Celeron N4020, 7.8 GB RAM, CPU-only, ~80 GB free. Used for
  development, unit tests, small-scale indexing, embeddings for small repos, and analysis.
- Kaggle: pending inspection (accelerator unknown). Used for the official-dataset run and any
  large embedding jobs. The design must degrade gracefully to CPU.

## 10. Limitations that may prevent a strong conclusion

- Small N per repository and few repositories → limited statistical power; we report CIs and
  avoid over-claiming significance.
- Patch-derived and automatically derived closure labels are proxies, not human judgements.
- Single-language (Python) and single-embedding-model scope; conclusions may not transfer.
- The official competition run cannot be executed locally without credentials; results on the
  released data are therefore prepared but reported as **not yet measured** unless executed.
- A 2-core CPU may make some embeddings slow; model choice is constrained by hardware.

## 11. What is already known vs. what experiments must establish

**Known (cited):** BM25 is a strong sparse baseline; RRF is an effective unsupervised fusion;
transformer embeddings help semantic code search; graph plug-ins help patch *generation*;
lexical retrieval dominates on the competition's issue-text localization.

**To be established here:** whether a model-agnostic graph-guided hybrid improves the
*closure* objective; the shape of the recall-vs-budget curve; whether `module`/`async` nodes
and typed `imports` edges add measurable value over call-only graphs; and whether any gain is
robust across repositories.
