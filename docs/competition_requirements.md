# Verified Competition Requirements

**Verification date:** 2026-10-19 (UTC)
**Verified by:** automated research agent (OpenCode), via official Kaggle pages and public
Kaggle web-search excerpts of those pages. No competition data was downloaded.

> Status legend: **[VERIFIED]** = read directly from an official Kaggle page or reproduced
> from an independent public mirror of that page; **[REPORTED]** = stated by a third party
> (community notebook/repo); **[UNRESOLVED]** = could not confirm.

---

## 1. Target

- Competition: **Google - The Gemma 4 Developer Agent Paper Track**
- Canonical URL: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper
  **[VERIFIED: page title returned by fetch = "Google - The Gemma 4 Developer Agent Paper Track | Kaggle"]**
- Companion competition: **Google - The Gemma 4 Developer Agent Competition**
  https://www.kaggle.com/competitions/gemma-4-developer-agent
- Sponsor: **Google LLC / Google DeepMind** **[VERIFIED]**
- The two competitions are **separate**. The Paper Track is entered by joining the
  paper-track competition and submitting a **Kaggle Writeup**. Entering/competing in the
  main competition does **not** automatically enter the paper track, and vice versa.
  **[VERIFIED from paper-track tracks-and-awards page]**

## 2. Prizes (Paper Track) **[VERIFIED]**

Total: **$35,000**

| Award | Amount | Definition (verbatim intent) |
|---|---|---|
| Overall Best Paper | $15,000 | Highest average across the five evaluation criteria |
| **Best New Resource (Dataset, library, etc)** | **$10,000** | "A resource introduces a new dataset, tool, or software... compared to an empirical paper which generates new knowledge/experiments." |
| Best New Application | $10,000 | — |

> The paper track states: "Submissions for Paper Awards are evaluated equally across the
> following five criteria." **The exact five criteria names were not fully captured
> [UNRESOLVED — see §7].** Community descriptions of the companion competition list the
> encouraged research topics (see §3), which strongly overlap with the criteria themes.

- Winner license: **Open Source Apache 2.0** **[VERIFIED from rules page]**

## 3. Encouraged research topics (paper track) **[VERIFIED]**

Participants are encouraged to submit original, unpublished research on topics including
but not limited to:

- **Tuning & Optimization:** PEFT and RL approaches tailored to improve SWE-agent capability.
- **Code Comprehension:** Novel techniques for **code-graph generation, parsing, and
  embedding** to enhance deep comprehension of complex repositories.
- **Tasks & Benchmarks:** Development of **new tasks, evaluation datasets, or resources**
  targeting code structure, graphs, and structured code generation.
- **Graph Reasoning:** Methods and architectures for improving LLM reasoning over
  large-scale graphs.

> "Submissions leveraging the accompanying released graph and embedding dataset are highly
> encouraged, but not a requirement for submission." **[VERIFIED]**
> This sentence is the clearest official signal about what a strong resource contribution
> should build on.

## 4. Submission mechanics (paper track) **[VERIFIED]**

- A valid submission = a **Kaggle Writeup** documenting the research, shared by the deadline.
- Optional: instead of writing the paper in the Writeup, upload an **arXiv-ready (LaTeX/Word)
  PDF** via the **Public Project Link** feature. It must be publicly accessible and require
  no login or paywall.
- A **public Kaggle Notebook** and/or **public project link** are optional but permitted.
- Draft/un-submitted Writeups at the deadline are **not** judged.
- If a private Kaggle Resource is attached to a public Writeup, the resource is automatically
  made public after the deadline.

## 5. Timeline **[VERIFIED]**

| Date | Event |
|---|---|
| 2026-09-23 | Start date |
| **2026-11-12 23:59 UTC** | **Research Paper (Writeup) deadline** — hard target for this project |
| 2026-11-25 | Entry deadline (must accept rules) |
| 2026-11-25 | Team merger deadline |
| 2026-12-02 | Final Submission Deadline (main competition) |

- 2026-11-12 23:59 UTC = **2026-11-13 05:29 IST**. Internal working deadline for this
  project is **2026-11-10** to leave margin.

## 6. Rules relevant to research conduct **[VERIFIED]**

- **External data is allowed** — general competition rules: "You may use data other than
  the Competition Data ('External Data') to develop and test your Submissions."
- Competition Data may be used for research/education and commercial purposes.
- **Data Security clause:** participants agree to use reasonable measures to prevent persons
  who have not agreed to the rules from gaining access to Competition Data, and to notify
  Kaggle of unauthorized transmission. → **We must not redistribute competition data**; we
  may point users to obtain it themselves from Kaggle.
- The delivered software code must follow the sponsor's documentation guidelines, must be
  capable of generating the winning submission, and must describe the resources required to
  build/run it successfully.

## 7. Unresolved / to re-verify before submission

1. **Exact names of the five evaluation criteria** and any rubric weights. The page says
   "evaluated equally across the following five criteria" but the list text was not captured
   in full through the accessible fetch. **Action:** open the paper-track Writeup page in a
   logged-in browser and transcribe the five criteria verbatim before final submission.
2. Exact word limit for the Writeup body (task brief states **3,000 words**; not independently
   re-verified on the official page).
3. Whether a public notebook/project link materially affects scoring (currently described only
   as "optional").
4. Whether the paper track requires accepting separate rules beyond joining.

## 8. Companion dataset facts (main competition) — relevant to this resource **[VERIFIED]**

Source: https://www.kaggle.com/competitions/gemma-4-developer-agent/data

- Purpose: SWE agents solving real Python bug fixes/feature requests; SWE-bench-style
  PASS/FAIL grading on hidden tests.
- **Public development set = 129 tasks** in `tasks.jsonl`.
- Fields: `instance_id`, `repo`, `base_commit`, `problem_statement`, `hints_text`, `patch`
  (reference fix), `test_patch` (verification tests), `created_at`.
- Repositories: `fastapi/fastapi`, `Textualize/rich`, `psf/requests`, `encode/httpx`.
- `snapshots/`: 129 compressed Git working-tree archives frozen at `base_commit`, forward
  history removed.
- `graphs/`: **256 serialized NetworkX AST call/dependency graphs** (JSON), 129 task-named
  (`<instance_id>.json`) hard-linked to 127 commit-named
  (`<repo_short>_<base_commit>.json`). Schema:
  - `directed: true`, `multigraph: true`
  - `nodes[*].id` — fully qualified Python symbol path (module/class/function), e.g.
    `fastapi.routing._prepare_response_content`
  - `nodes[*].name` — human-readable qualified symbol name
  - `nodes[*].text` — full Python source of the definition at `base_commit`
  - `edges[*].source`, `edges[*].target` — directed structural (call/reference) relations
- The dataset also ships **node/graph embeddings** and specialized graph tools:
  - `get_code_neighbors(node, edge_type, max_neighbors=50)`
  - `search_similar_code(query, k=10)` — cosine similarity over **pre-computed** node embeddings
  - `get_code_subgraph(...)`
- The full Kaggle dataset download is **~21 GB** (tasks, snapshots, graphs, embeddings,
  wheels, docker specs, sample_submission). **[REPORTED by an independent community repo;
  not independently confirmed]**

### 8.1 Known limitations of the released graphs/embeddings **[REPORTED — independent community notebooks]**

These are third-party observations, used here only to motivate research hypotheses, not
asserted as official facts:

- The released graphs contain **only call edges**; they reportedly have **no module nodes**
  and **no async functions**, so the graph tools cannot reach async code.
- On the official 129 tasks, a community localization benchmark reported **file
  recall@1/@5**: TF-IDF 0.21/0.50, embedding 0.05/0.21, PPR 0.08/0.26, hybrid 0.14/0.42 —
  i.e. **lexical retrieval dominated and the released embeddings were weak for issue text**.
- A separate notebook reported **function-level H@1 = 0.238** using BM25/graph-hop pools after
  stripping URLs from issues.

> These reports motivate (a) testing whether structural signals can compensate for weak
> semantic recall, and (b) the value of a **reusable, fair, file- and symbol-level retrieval
> benchmark harness** that separates retrieval quality from patch success. They are treated
> as prior evidence to be re-tested, not as established results.

## 9. Sources

- Paper track overview / tracks-and-awards:
  https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/tracks-and-awards
- Paper track rules: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/rules
- Main competition overview: https://www.kaggle.com/competitions/gemma-4-developer-agent/overview
- Main competition data: https://www.kaggle.com/competitions/gemma-4-developer-agent/data
- Main competition evaluation:
  https://www.kaggle.com/competitions/gemma-4-developer-agent/overview/evaluation
- Getting-started notebook (host): https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent
- Independent community mirror of rules/data notes:
  https://github.com/Gosling-dude/gemma4-developer-agent/blob/main/docs/competition_notes.md
  [REPORTED — used only for corroboration and clearly labelled]
