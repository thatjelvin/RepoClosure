# Novelty Assessment — RepoClosure

**Date:** 2026-10-19 · **Name status:** `RepoClosure` is provisional. A conflict check found
"RepoGraph" (ICLR 2025) and many "RepoLens"/"retrieval-bench"/"codeloc-bench" tools; the name
"RepoClosure" was chosen for low collision risk. A final trademark/GitHub name search is still
recommended before public release. The *contribution*, not the name, is what must be novel.

## 1. Closest competing resources

| Dimension | RepoGraph (Ouyang et al., ICLR 2025) | LocAgent (Chen et al., 2025) | SweRank (Reddy et al., 2025) | CoIR (Li et al., 2024) | codeloc-bench (Toussaint, 2026) | **RepoClosure (this work)** |
|---|---|---|---|---|---|---|
| Verifiable source | arXiv:2410.14684; github.com/ozyyshr/RepoGraph | arXiv:2503.09089 | arXiv:2505.07849 | arXiv:2407.02883; github.com/CoIR-team/coir | github.com/AntoineToussaint/codeloc-bench | this repo |
| Intended purpose | Plug-in repo graph to boost SWE-bench patch success | LLM agent that localizes code via a graph | Train a ranking model for issue localization | Benchmark of code-retrieval tasks | File-localization benchmark, SWE-bench gold patches | Model-agnostic retrieval toolkit + closure benchmark |
| Graph representation | Line-level nodes; def/ref edges; per-project filtering | Heterogeneous graph (dir/file/class/function); multi-hop | None (learned ranker) | None | None (uses file content) | Typed AST graph: nodes file/module/class/function/method; edges imports/contains/defines/calls/references, each with **provenance + confidence** |
| Retrieval methods | Graph ego-subgraph retrieval | LLM + graph traversal | Supervised cross-encoder ranker | Lexical/dense/sparse/late-interaction tasks | BM25, ripgrep, semble | BM25 + local embeddings + RRF fusion + budgeted graph expansion |
| Supported languages | Python (SWE-bench) | Python | Python (multilingual in v+) | Multi-language | Multi-language | Python first (pluggable) |
| Evaluation | SWE-bench patch success; CrossCodeEval | Localization acc. on SWE-bench/others | Localization (Acc@k, MRR) on SWE-bench | Many retrieval datasets | recall@k/NDCG@k on files | File + symbol localization **and context-closure recall**, with bootstrap CIs + paired tests |
| Reported limitations | Needs an LLM to consume graph; line-level graph, no closure metric | Needs a capable LLM; cost | Requires supervision/training; model, not a library | Snippet/function-level, not issue→repo-file | No graph; no closure objective; small self-reported table | Small N; proxy labels; single language; CPU-constrained embeddings |
| Licensing | MIT (repo) | Apache-2.0 (repo) | (check repo) | Apache-2.0 | (check repo) | Apache-2.0 (planned) |
| Remaining gap | No reusable retrieval benchmark; no closure objective; model-entangled | Not model-agnostic; heavy | Model, not a resource; no graph | No repository localization + graph closure | No graph signal; no closure metric | **Differentiated on the closure objective + explainable, model-agnostic graph retrieval + provenance-annotated graph** |
| Proposed contribution | — | — | — | — | — | See below |

Also examined and found to be less close, but relevant to positioning:
Reciprocal Rank Fusion (Cormack et al., SIGIR 2009) is the fusion primitive we use, not a
competitor. BEIR (Thakur et al., 2021) is a general IR benchmark. Repository-level Code Search
with Neural Retrieval Methods (Gandhi et al., 2025, arXiv:2502.07067) is BM25 + CodeBERT rerank
for file retrieval — a method, closest on method but with no graph/closure resource.

## 2. What is genuinely new here

1. **Mechanism + objective:** a *context-closure* retrieval objective (does the retriever
   surface the supporting entities reachable from the gold edit, not only the edit location),
   evaluated as a first-class complement to edit-location recall. To our knowledge no released
   resource frames repository retrieval this way.
2. **Provenance-annotated, confidence-graded graph:** every edge carries a provenance label
   (`ast_import`, `ast_contains`, `ast_defines`, `ast_call`, `name_heuristic`) and a confidence,
   so retrieval explanations can distinguish statically verified relations from heuristics.
   The released competition graph is reportedly calls-only with no module/async nodes; we add
   module and async-function nodes and `imports` edges.
3. **Explainable budgeted expansion:** each expanded entity carries the seed, the edge that
   pulled it in, the hop count, and the budget spent — an auditable context package for agents.
4. **Falsifiable claim:** we test — rather than assert — that graph structure improves the
   *closure* objective while contributing little to edit localization, and characterize when it
   hurts.

## 3. Explicitly NOT claimed as novel

- BM25, transformer embeddings, RRF, Personalized PageRank, AST parsing, or "hybrid retrieval"
  individually. These are prior art and are cited as such.
- The mere idea of a code retrieval benchmark (many exist).
- Any claim of downstream patch-fixing superiority unless measured.

## 4. References (verified)

- Ouyang, S., Yu, W., Ma, K., Xiao, Z., Zhang, Z., Jia, M., Han, J., Zhang, H., Yu, D. (2025).
  *RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph.* ICLR 2025.
  arXiv:2410.14684. https://arxiv.org/abs/2410.14684
- Chen, Z., Tang, X., Deng, G., Wu, F., Wu, J., Jiang, Z., Prasanna, V., Cohan, A., Wang, X.
  (2025). *LocAgent: Graph-Guided LLM Agents for Code Localization.* arXiv:2503.09089.
- Reddy, R. G., Suresh, T., Doo, J., Liu, Y., Nguyen, X. P., Zhou, Y., Yavuz, S., Xiong, C.,
  Ji, H., Joty, S. (2025). *SweRank: Software Issue Localization with Code Ranking.*
  arXiv:2505.07849.
- Li, X., Dong, K., Lee, Y. Q., Xia, W., Zhang, H., Dai, X., Wang, Y., Tang, R. (2024).
  *CoIR: A Comprehensive Benchmark for Code Information Retrieval Models.* arXiv:2407.02883.
- Gandhi, S., Gao, L., Callan, J. (2025). *Repository-level Code Search with Neural Retrieval
  Methods.* arXiv:2502.07067.
- Cormack, G. V., Clarke, C. L. A., Buettcher, S. (2009). *Reciprocal Rank Fusion outperforms
  Condorcet and individual Rank Learning Methods.* SIGIR '09, 758–759.
  DOI 10.1145/1571941.1572114.
- Thakur, N., Reimers, N., Rücklé, A., Srivastava, A., Gurevych, I. (2021). *BEIR: A
  Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models.*
  arXiv:2104.08663.

(Full reference list with all sources lives in `paper/manuscript.md`.)
