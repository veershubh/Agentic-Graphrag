# Multi-Hop Agentic RAG with Evals: 8-Week Implementation Plan

**Goal:** Build an agentic multi-hop RAG system (graph + vector retrieval) with an evaluation, observability, and CI layer, deployed with a live demo. The finished project should support one resume bullet backed by real numbers.

**Assumed defaults (swap freely):**

| Item | Default |
|---|---|
| Corpus | 300-500 arXiv papers on one niche (e.g. LLM evaluation) |
| Language | Python |
| Graph + vectors | Neo4j (graph and native vector index in one store) |
| LLM | Local Ollama models (Qwen3 4B for extraction/planning, Qwen3 8B for answers) |
| Serving | FastAPI + Docker |
| Observability | Local run records with tokens and latency |
| CI | GitHub Actions |
| Agent | Plain Python state machine or LangGraph (check current versions before pinning) |

---

## Architecture

```
Question -> Planner (decompose, choose tools)
              |- vector_search   (chunks)
              |- graph_expand    (entity -> N hops -> linked chunks)
              |- keyword_search  (BM25)
           -> Rerank -> Answer with citations (or abstain)

Every step logged locally | API cost and latency logged | eval suite gates CI
```

---

## Phase 0: Setup (Days 1-3)

- [x] Create repo with folders: `ingest/ extract/ graph/ retrieval/ agent/ eval/ api/ ui/ configs/ docs/`
- [x] Put model names, temperature (use 0), chunk size, and k in config files
- [x] Write a one-page problem statement and success metrics before coding
- [x] Set up environment, secrets handling, and a `.env.example`
- [x] Run an empty pipeline end-to-end on 5 documents

**Exit criterion:** the pipeline runs end-to-end on 5 documents.

---

## Phase 1: Data and Evals First (Week 1)

Build the test before the system.

**Track A: credibility (public benchmark)**
- [x] Sample 300 questions from MuSiQue or 2WikiMultiHopQA
- [x] Load their supporting paragraphs as a separate corpus

**Track B: real domain**
- [ ] Download and clean 300-500 papers; store metadata (title, authors, year, id)
- [x] Write 100-150 questions over the corpus, tagged 1-hop / 2-hop / 3-hop
- [x] Include 10-15% unanswerable questions to test abstention
- [ ] Generate questions from raw passage sets, NOT from your own graph (avoids circular evaluation)
- [x] Hand-verify every question and gold answer
- [x] Freeze and version the eval files in `eval/data/`

**Exit criterion:** frozen, versioned eval files for both tracks.

---

## Phase 2: Baseline RAG + Eval Harness (Week 2)

- [x] Chunk (~500 tokens with overlap), embed, store, retrieve top-k, generate
- [x] Add hybrid retrieval: BM25 + dense with reciprocal rank fusion (a stronger baseline makes later gains more credible)
- [ ] Build the harness with these metrics:
  - [x] Exact match and F1
  - [x] Supporting-document recall@k
  - [ ] Faithfulness (LLM judge, calibrated against ~50 human-labeled answers)
  - [x] Cost per query
  - [x] Latency (p50 / p95)
- [x] Split reported metrics by hop count
- [x] Add bootstrap confidence intervals
- [x] Make one command produce a results table

**Exit criterion:** `make eval` outputs a baseline results table.

**Progress (2026-09-29):** BM25, pinned local dense embeddings, and BM25+dense RRF have been evaluated on the public MuSiQue slice. Supporting-document recall@5 is reported by hop count with paired bootstrap intervals in `eval/results/public_hybrid_v0.1.json`. On the same first 30 two-hop questions, local Qwen3 4B scored EM/F1 0.000/0.000 and Qwen3 8B scored 0.067/0.165. A stratified Qwen3 8B sample of 10 questions per hop bucket scored overall EM/F1 0.100/0.216, with a 95% F1 interval of 0.112–0.335. A deterministic 30-question domain sample (10 per hop) using BM25 passages scored EM/F1 0.000/0.287; hop-wise F1 was 0.343/0.384/0.134, citation validity 0.933 overall, and mean latency 17.38s (one long retry reached 127.54s). All used local inference at zero model API cost. Full records are in `eval/results/public_answer_qwen3_*.json` and `eval/results/domain_answer_qwen3_8b_stratified_v0.1.json`. Answer quality remains inadequate; calibrated faithfulness and broader evaluation remain incomplete.

**Progress (2026-10-01):** `python eval/build_results_report.py` now compiles the frozen public/domain retrieval artifacts and selected answer runs into `eval/results-summary.md`, including per-hop recall/F1, confidence intervals where available, latency, and model API cost. It reads existing artifacts only and does not invoke models.

**Progress (2026-10-20):** Added a root `Makefile` `eval` target that writes the public BM25 baseline to ignored `data/processed/make_eval_public_bm25.json`, preserving frozen eval inputs and committed results. The equivalent command was run successfully: recall@5 was 0.429 overall and 0.575/0.403/0.310 for 2/3/4-hop questions. GNU Make is not installed in this Windows environment, so the target itself could not be invoked here. Also corrected `eval/run_agent_eval.py` to read planner and answer model names from the supplied config instead of hardcoding them into result metadata.

---

## Phase 3: Graph Construction (Weeks 3-4)

**Schema and extraction**
- [x] Define a constrained ontology
  - Entities: Paper, Method, Dataset, Metric, Task
  - Relations: PROPOSES, EVALUATES_ON, USES, OUTPERFORMS, CITES
- [x] Implement per-chunk triple extraction with structured JSON output (cheaper model)
- [x] Implement extraction caching by prompt, model, chunk ID, and content hash
- [x] Pilot on 20 documents, measure cost, extrapolate, then scale

**Entity resolution**
- [x] Normalize names by case and punctuation
- [x] Implement embedding-based duplicate candidate generation for review
- [ ] Adjudicate ambiguous pairs with an LLM
- [x] Maintain a conservative alias table; emit collisions for review
- [ ] Hand-label 100 pairs; report resolution precision and recall

**Storage and quality**
- [ ] Load into Neo4j; link every node and edge to its source chunk and document
- [ ] Hand-audit 50 random triples; record the accuracy
- [ ] Record total extraction cost and time

**Exit criterion:** graph loaded, with audit accuracy and extraction cost documented.

**Progress (2026-09-29):** The balanced local pilot processed all 197 available passages from 20 papers using Ollama/Qwen3 4B. Cached model latency totals 3,189 seconds (about 16.2 seconds per passage), with zero model API charges. It produced 1,734 entity mentions; 636 of 1,362 candidate triples passed ontology checks and 726 were rejected. Consolidation produced 994 nodes, 581 edges, and 103 unresolved alias collisions. Local embedding candidate generation produced 307 review pairs, and a 50-edge audit worksheet is ready for human labels. The extraction run and cost measurement are complete, but the rejection rate and unaudited output prevent scaling. The Neo4j loader dry run processed nine batches; actual loading, human audits, and candidate adjudication remain incomplete.

**Progress (2026-10-20):** Full extraction completed for all 3,203 selected passages across 325 papers. The content-addressed cache refresh reused 3,192 records and recomputed 11 previously head/tail-truncated records with overlapping windows; final metadata reports zero truncations. Extraction produced 20,435 entity mentions, 7,240 accepted triples, and 8,819 rejected triples. Consolidation produced 10,798 nodes, 6,637 edges, 7,139 edge-evidence rows, 10,977 aliases, and 1,182 ambiguous aliases. Linkage validation against the 10,878-passage inventory found no missing source chunk IDs in node or edge evidence. Full-coverage retrieval on the same 98 frozen answerable questions scored 0.349 graph-only and 0.583 BM25+graph RRF against 0.549 BM25; hop breakdown for all eight variants is in `docs/domain-full-graph-retrieval-comparison.md`. Dense-only remains 0.224, while BM25+dense RRF is 0.398; graph+dense fusion results are reported in the same file. The pinned model, normalized cosine vectors, row IDs, and content hashes align; the domain dense result still needs relevance-fit analysis before any quality claim. A tokenizer length warning was traced to deliberate full-text token scanning before windowing; the scan now suppresses that misleading warning, and each tested window stays within the 256-token model limit. The detailed extraction, retrieval examples, and leakage analysis are recorded in `docs/retrieval-debug.md`; ambiguous aliases and extraction accuracy still need human adjudication. PR [#1](https://github.com/veershubh/Agentic-Graphrag/pull/1) remains open, targets `main`, and is synchronized; the legacy `fix/retrieval-debug` work is already in `main`. Public retrieval quality CI passed on the graph-extraction change. Local validation includes five extraction tests, compile checks, diff checks, public BM25 floors, the smoke pipeline, API/UI checks, and loader dry-run. Docker and a live Neo4j instance are unavailable here, so packaging and a live load remain incomplete.

**Progress (2026-10-20):** Added `docs/failure-analysis.md`, a 30-case first-pass triage of the saved stratified BM25 answer run. It separates the evidence coverage facts (9/30 full support, 17/30 partial, 4/30 none) from exact-match outcomes and documents examples where EM is misleading or answer generation fails despite retrieved support. This does not complete the plan's graph-specific causal labels (extraction, linking, decomposition, expansion, generation); those require graph-agent traces and human review.

---

## Phase 4: Hybrid and Agentic Retrieval (Weeks 4-5)

**Progress (2026-09-29):** A bounded in-memory graph expansion index, fixed BM25+graph RRF retriever, and domain graph retrieval evaluation command are implemented, with optional dense passage rankings and external entity seeds. The expanded 197-passage graph evaluated at 0.041 graph-only supporting recall@5; BM25+graph RRF scored 0.435 versus 0.549 for BM25 (paired difference -0.114, 95% CI -0.179 to -0.054). Even with more extraction coverage, this unaudited graph underperformed the baseline; improve extraction and entity resolution quality before relying on graph expansion.

**Fixed hybrid pipeline**
- [x] Vector search finds seed entities and chunks
- [x] Expand 1-2 hops in the graph
- [x] Collect linked chunks, then rerank
- [x] Cap expansion (max nodes and max chunks) so context doesn't flood

**Agentic pipeline**
- [x] Planner decomposes the question into sub-questions
- [x] Planner picks a tool per sub-question (vector, graph, keyword)
- [x] Set a step budget (e.g. 5 steps) and a stop condition
- [x] Add an explicit "insufficient evidence" exit
- [x] Require citations in the answer
- [x] Verify every cited chunk was actually retrieved

**Progress (2026-09-29):** A bounded single-query controller is implemented with keyword/vector/graph tool routing, a configurable step budget, early finish and insufficient-evidence behavior, citation validation, and local token/latency reporting. One verified domain query completed locally in 94 seconds with a warm embedding cache; it returned a relevant answer with valid citations. Building the 10,878-passage embedding cache took about 14 minutes once. A short planner query fell back to the user question, and final context prioritizes recent search results after the first run exposed irrelevant-context contamination. This is a wiring check, not an accuracy result; broader agent evaluation remains.

**Progress (2026-09-29):** A three-question, one-per-hop agent pilot now runs through the answer metric harness. Token F1 was 0.222 versus 0.315 for BM25 answers on the same questions; supporting recall was 0.667 versus 0.611, while mean latency rose from 14.4s to 77.4s. This tiny pilot does not show an agent quality improvement. Planner evidence and history are capped to avoid exceeding Ollama's 4,096-token context; a three-hop question that previously hit the limit completed after the cap.

**Exit criterion:** both retrievers run through the same eval harness.

**Progress (2026-10-01):** The fixed hybrid now also retrieves graph seed entities from dense vectors over entity names and aliases, expands those entities under configured node/chunk caps, and fuses linked chunks with BM25 and dense passage rankings. On the same 98 answerable questions, dense-seeded graph-only recall@5 was 0.024; BM25+dense+graph with dense entity seeds scored 0.340, versus 0.349 for the BM25-seeded graph variant and 0.549 for BM25. This completes the bounded fixed-hybrid retrieval path but shows no improvement on this unaudited pilot. Results and cache metadata are in `eval/results/domain_graph_dense_entity_seed_v0.1.json`.

**Progress (2026-10-01):** The fixed hybrid now also runs through the same answer metrics on the identical 30-question stratified domain sample as the BM25 answer baseline. Fixed hybrid token F1 was 0.289 (95% CI 0.219–0.361) versus 0.287 (0.207–0.371) for BM25; paired F1 difference was +0.002 (95% CI -0.074 to +0.080), so the sample does not show an answer-quality improvement. Its supporting recall on this sample was 0.244 versus 0.556 for BM25. Mean answer-generation latency was 16.1s; retrieval was precomputed. The machine-readable answer run is in `eval/results/domain_fixed_hybrid_answer_qwen3_8b_v0.1.json`.

---

## Phase 5: Ablations and Analysis (Week 6)

- [x] Run initial variants:
  - [x] Vector-only
  - [x] BM25 + vector
  - [x] Graph-only
  - [x] Fixed hybrid
  - [x] Agentic (three-question wiring pilot; not a full ablation)
- [x] Vary hop depth (1 vs 2) and top-k
- [x] Produce tables and charts split by hop count
- [ ] Categorize 30-50 wrong answers by cause:
  - extraction miss
  - entity-resolution error
  - bad decomposition
  - expansion noise
  - generation error
- [x] Document where GraphRAG does NOT help (negative results are strong interview material)

**Progress (2026-09-29):** On the 98-answerable-question domain track, BM25 recall@5 was 0.549; dense-only was 0.175, BM25+dense RRF 0.327, graph-only 0.041, BM25+graph RRF 0.435, and BM25+dense+graph RRF 0.349. Paired bootstrap intervals are recorded in `eval/README.md` and result artifacts. The 1-vs-2-hop sweep tied at top-5 under current expansion caps; top-k 3/5/10 results are versioned. A three-question agent pilot scored F1 0.222 vs BM25's 0.315 on the same items and took 77.4s vs 14.4s mean latency. These limited runs document negative results rather than a gain; answer-level fixed-hybrid and broader agent ablations remain open.

**Progress (2026-10-20):** Added `eval/build_retrieval_charts.py` and the two hop-split SVGs in `docs/retrieval-ablation-charts.md`, using only the existing public/domain retrieval artifacts. The SVGs passed XML parsing. They are explicitly labeled as prior provisional results; the full-coverage graph evaluation will be added as a separate result after extraction finishes.

**Progress (2026-10-20):** Added `eval/build_retrieval_comparison.py` for the requested before/after table. It checks question and passage hashes, settings, variants, and per-question IDs before writing a report. A smoke comparison using the same baseline artifact on both sides passed; the final report will be generated only after the new full-coverage graph artifact exists.

**Exit criterion:** a results section you can defend line by line.

---

## Phase 6: Observability, Local Runtime, Guardrails (Weeks 6-7)

**Tracing**
- [x] Trace every LLM and tool call locally, with tokens, latency, and zero model API cost per query
- [x] Document one failure from symptom to root cause using a trace

**Local runtime controls**
- [x] Run extraction, planning, and answer generation through loopback Ollama
- [x] Cache extraction results by prompt, model, and input content
- [x] Measure local memory, latency, and power use; hosted model API spend is zero

**Guardrails**
- [x] Plant prompt-injection text in a few documents; verify the system ignores it
- [x] Test abstention on the unanswerable set
- [x] Enforce citation checks

**Progress (2026-10-01):** Five synthetic passages contained instructions to override the answer policy, reveal the system prompt, suppress citations, or return a canary answer. Local Qwen3 8B passed all five configured checks: each answer cited the evidence passage and did not repeat the canary, cite the attack passage, or echo a system-prompt request. This is a small smoke check, not a comprehensive prompt-injection assessment. Run with `python eval/run_prompt_injection_eval.py`; output is versioned in `eval/results/prompt_injection_qwen3_8b_v0.1.json`.

**Exit criterion:** a documented traced failure, plus measured local resource use.

---

## Phase 7: CI and Deployment (Weeks 7-8)

**Progress (2026-09-29):** A GitHub Actions workflow now runs the full public BM25 retrieval evaluation for relevant pull requests, nightly, or manually, then enforces conservative overall and hop-specific recall floors. This is a retrieval-only gate; the planned cached answer/faithfulness evaluation and graph/agent checks remain pending.

**Progress (2026-09-29):** The local Qwen3 8B answerer was evaluated on all 11 frozen unanswerable domain probes with BM25 evidence. It abstained end-to-end on 7/11; two of those were fail-closed truncated outputs, and the model itself abstained on 5/9 successfully generated responses. Four unsupported answers show abstention remains unreliable. The run and error flags are versioned in `eval/results/domain_unanswerable_qwen3_8b_v0.1.json`.

**Progress (2026-09-29):** BM25 top-score threshold analysis found overlapping answerable/unanswerable score ranges. Rejecting all 11 negative probes in-sample retained only 45.9% of answerable questions; no confidence cutoff is enabled. Results are in `eval/results/domain_abstention_threshold_v0.1.json`.

**Progress (2026-09-29):** A local FastAPI scaffold now wraps the CLI agent with health/readiness reporting, question length limits, a five-requests-per-minute cap, one concurrent run by default, and a request timeout. It only accepts a loopback Ollama endpoint and is documented to bind on `127.0.0.1`. The route has not been run in an installed FastAPI environment; Docker, the UI, auth/TLS, and public deployment remain open.

**Progress (2026-09-29):** A same-origin static UI is served from `/` and presents answers/abstentions, citations, and the planner's search-tool path. It uses browser text nodes for model output and makes no third-party asset requests. It has not yet been browser-verified or packaged in Docker.

**Progress (2026-09-29):** The API appends a local metadata-only trace for each completed request, including model/token counts, tool names, latency, stop reason, citation validity, and zero API cost without storing question or answer text.

**Progress (2026-10-20):** Verified a saved CLI agent trace with per-planner-call response IDs, tokens, latency, tool/query results, and answer usage. Added `docs/agent-trace-failure.md`, tracing a duplicate keyword-planning step to the planner's one-word query and the controller's short-query fallback; the repeat guard stopped the second search before execution. This single example documents an efficiency failure, not a general accuracy claim.

**Progress (2026-10-20):** Added `docs/local-resource-snapshot.md` with a 12-second active-extraction sample on the RTX 4050 laptop GPU, recent extraction-call latency distribution, and one agent end-to-end measurement. This is a local workload snapshot; whole-device energy and the full-run extraction summary remain open until extraction completes.

**CI**
- [ ] GitHub Actions runs a small cached eval (~30 questions) on each PR
- [ ] Fail the build if F1 or faithfulness drops below threshold (leave a margin for LLM nondeterminism)
- [ ] Run the full eval manually or nightly

**Deployment**
- [ ] FastAPI service in Docker
- [x] Simple local UI showing the answer, citations, and agent search path
- [x] Add rate limiting
- [x] Limit local request duration and concurrency so a public link can't overload the host machine
- [ ] Deploy to a public URL
- [ ] Record a 2-minute demo video

**Exit criterion:** public URL, demo video, green CI badge.

---

## Phase 8: Packaging (Week 8)

**README structure**
- [x] Problem statement
- [x] Results table (by hop count, with confidence intervals)
- [x] Architecture diagram
- [x] How to reproduce
- [x] Failure gallery (5 real misses and their observable failure modes)
- [x] Cost and latency
- [x] Limitations

**Progress (2026-10-01):** The README states the research question and current negative domain result, links the generated hop-split report, shows the end-to-end architecture, gives commands to reproduce public retrieval, and summarizes measured latency/cost and limitations.

**Progress (2026-10-20):** Added a five-case failure gallery in the README from the saved domain BM25 sample, with detailed support coverage and answer evidence in `docs/failure-analysis.md`. It does not claim graph-specific or trace-confirmed root causes; those remain open.

**Progress (2026-10-20):** Drafted `docs/blog-draft.md` and `docs/interview-prep.md` with current measurements, negative findings, and open audit limits. The blog is a local draft, not published. Updated the README public fusion recall to the exact artifact value (0.4925), avoiding a rounding difference with the generated three-decimal table.

**Extras**
- [x] Draft a short blog post on what you learned, including negative results
- [ ] Pin the repo and add the live demo link to your profile

**Interview prep: rehearse five trade-off stories**
- [ ] Why a constrained schema
- [ ] How entity resolution was validated
- [ ] When the agent beat fixed hybrid, and at what cost
- [ ] One regression CI caught
- [ ] One thing you'd do differently

---

## Results Table Template

| Variant | F1 (all) | F1 (2-hop) | F1 (3-hop) | Recall@5 | Faithfulness | Cost / query | p95 latency |
|---|---|---|---|---|---|---|---|
| Vector-only | | | | | | | |
| BM25 + vector | | | | | | | |
| Graph-only | | | | | | | |
| Fixed hybrid | | | | | | | |
| Agentic | | | | | | | |

---

## Common Failure Modes

- Building the graph before the eval set, so you can't tell whether it helps
- Benchmarking only on your own questions, or only on the public set
- Unbounded extraction spend (pilot first, then scale)
- Skipping entity resolution, then blaming the graph for noisy results
- Over-scoping: if time slips, cut UI polish or multi-agent extras before cutting evals or ablations

---

## Definition of Done

- [ ] Public repo, live demo, and CI badge
- [x] Results on both a public benchmark and your domain set, split by hop count
- [x] At least four ablation variants with confidence intervals
- [ ] Hand-audited extraction and entity-resolution accuracy
- [x] Traced, documented failure analysis
- [x] Drafted one resume bullet backed by real numbers:

> "Built an agentic multi-hop RAG system (graph + vector retrieval) over [corpus]; designed a [N]-question eval suite with CI regression gating, raising F1 from X to Y on 3-hop questions while cutting per-query cost by Z% through caching and routing. Deployed with full tracing."

---

## Timeline at a Glance

| Week | Focus |
|---|---|
| 0 (days 1-3) | Setup |
| 1 | Eval datasets |
| 2 | Baseline RAG + harness |
| 3-4 | Graph construction, entity resolution |
| 4-5 | Hybrid + agentic retrieval |
| 6 | Ablations, failure analysis, start observability |
| 7 | Cost, guardrails, CI |
| 8 | Deployment, README, blog, interview prep |
