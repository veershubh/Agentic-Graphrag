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

- [ ] Create repo with folders: `ingest/ extract/ graph/ retrieval/ agent/ eval/ api/ ui/ configs/ docs/`
- [ ] Put all model names, temperature (use 0), chunk size, and k in config files, not code
- [ ] Write a one-page problem statement and success metrics before coding
- [ ] Set up environment, secrets handling, and a `.env.example`
- [ ] Run an empty pipeline end-to-end on 5 documents

**Exit criterion:** the pipeline runs end-to-end on 5 documents.

---

## Phase 1: Data and Evals First (Week 1)

Build the test before the system.

**Track A: credibility (public benchmark)**
- [ ] Sample 300 questions from MuSiQue or 2WikiMultiHopQA
- [ ] Load their supporting paragraphs as a separate corpus

**Track B: real domain**
- [ ] Download and clean 300-500 papers; store metadata (title, authors, year, id)
- [ ] Write 100-150 questions over the corpus, tagged 1-hop / 2-hop / 3-hop
- [ ] Include 10-15% unanswerable questions to test abstention
- [ ] Generate questions from raw passage sets, NOT from your own graph (avoids circular evaluation)
- [ ] Hand-verify every question and gold answer
- [ ] Freeze and version the eval files in `eval/data/`

**Exit criterion:** frozen, versioned eval files for both tracks.

---

## Phase 2: Baseline RAG + Eval Harness (Week 2)

- [ ] Chunk (~500 tokens with overlap), embed, store, retrieve top-k, generate
- [x] Add hybrid retrieval: BM25 + dense with reciprocal rank fusion (a stronger baseline makes later gains more credible)
- [ ] Build the harness with these metrics:
  - [ ] Exact match and F1
  - [x] Supporting-document recall@k
  - [ ] Faithfulness (LLM judge, calibrated against ~50 human-labeled answers)
  - [ ] Cost per query
  - [ ] Latency (p50 / p95)
- [ ] Split every metric by hop count
- [ ] Add bootstrap confidence intervals
- [ ] Make one command produce a results table

**Exit criterion:** `make eval` outputs a baseline results table.

**Progress (2026-09-29):** BM25, pinned local dense embeddings, and BM25+dense RRF have been evaluated on the public MuSiQue slice. Supporting-document recall@5 is reported by hop count with paired bootstrap intervals in `eval/results/public_hybrid_v0.1.json`. On the same first 30 two-hop questions, local Qwen3 4B scored EM/F1 0.000/0.000 and Qwen3 8B scored 0.067/0.165. A stratified Qwen3 8B sample of 10 questions per hop bucket scored overall EM/F1 0.100/0.216, with a 95% F1 interval of 0.112–0.335. All used local inference at zero model API cost. Full records are in the `eval/results/public_answer_qwen3_*.json` files. Answer quality remains inadequate; calibrated faithfulness and broader evaluation remain incomplete.

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

---

## Phase 4: Hybrid and Agentic Retrieval (Weeks 4-5)

**Progress (2026-09-29):** A bounded in-memory graph expansion index, fixed BM25+graph RRF retriever, and domain graph retrieval evaluation command are implemented, with optional dense passage rankings and external entity seeds. The expanded 197-passage graph evaluated at 0.041 graph-only supporting recall@5; BM25+graph RRF scored 0.435 versus 0.549 for BM25 (paired difference -0.114, 95% CI -0.179 to -0.054). Even with more extraction coverage, this unaudited graph underperformed the baseline; improve extraction and entity resolution quality before relying on graph expansion.

**Fixed hybrid pipeline**
- [ ] Vector search finds seed entities and chunks
- [ ] Expand 1-2 hops in the graph
- [ ] Collect linked chunks, then rerank
- [ ] Cap expansion (max nodes and max chunks) so context doesn't flood

**Agentic pipeline**
- [ ] Planner decomposes the question into sub-questions
- [ ] Planner picks a tool per sub-question (vector, graph, keyword)
- [ ] Set a step budget (e.g. 5 steps) and a stop condition
- [ ] Add an explicit "insufficient evidence" exit
- [ ] Require citations in the answer
- [ ] Verify every cited chunk was actually retrieved

**Progress (2026-09-29):** A bounded single-query controller is implemented with keyword/vector/graph tool routing, a configurable step budget, early finish and insufficient-evidence behavior, citation validation, and local token/latency reporting. One verified domain query completed locally in 94 seconds with a warm embedding cache; it returned a relevant answer with valid citations. Building the 10,878-passage embedding cache took about 14 minutes once. A short planner query fell back to the user question, and final context prioritizes recent search results after the first run exposed irrelevant-context contamination. This is a wiring check, not an accuracy result; broader agent evaluation remains.

**Exit criterion:** both retrievers run through the same eval harness.

---

## Phase 5: Ablations and Analysis (Week 6)

- [x] Run initial variants:
  - [x] Vector-only
  - [x] BM25 + vector
  - [x] Graph-only
  - [ ] Fixed hybrid
  - [ ] Agentic
- [x] Vary hop depth (1 vs 2) and top-k
- [ ] Produce tables and charts split by hop count
- [ ] Categorize 30-50 wrong answers by cause:
  - extraction miss
  - entity-resolution error
  - bad decomposition
  - expansion noise
  - generation error
- [ ] Document where GraphRAG does NOT help (negative results are strong interview material)

**Progress (2026-09-29):** On the 98-answerable-question domain track, BM25 recall@5 was 0.549; dense-only was 0.175, BM25+dense RRF 0.327, graph-only 0.041, BM25+graph RRF 0.435, and BM25+dense+graph RRF 0.349. Paired bootstrap intervals are recorded in `eval/README.md` and result artifacts. The 1-vs-2-hop sweep tied at top-5 under current expansion caps; top-k 3/5/10 results are versioned. All measured additions underperformed BM25 on this provisional domain dataset, so these runs document negative results rather than a gain. Agentic and broader fixed hybrid ablations remain open.

**Exit criterion:** a results section you can defend line by line.

---

## Phase 6: Observability, Local Runtime, Guardrails (Weeks 6-7)

**Tracing**
- [ ] Trace every LLM and tool call locally, with tokens, latency, and zero model API cost per query
- [ ] Document one failure from symptom to root cause using a trace

**Local runtime controls**
- [x] Run extraction, planning, and answer generation through loopback Ollama
- [x] Cache extraction results by prompt, model, and input content
- [ ] Measure local memory, latency, and power use; hosted model API spend is zero

**Guardrails**
- [ ] Plant prompt-injection text in a few documents; verify the system ignores it
- [ ] Test abstention on the unanswerable set
- [ ] Enforce citation checks

**Exit criterion:** a documented traced failure, plus measured local resource use.

---

## Phase 7: CI and Deployment (Weeks 7-8)

**Progress (2026-09-29):** A GitHub Actions workflow now runs the full public BM25 retrieval evaluation for relevant pull requests, nightly, or manually, then enforces conservative overall and hop-specific recall floors. This is a retrieval-only gate; the planned cached answer/faithfulness evaluation and graph/agent checks remain pending.

**CI**
- [ ] GitHub Actions runs a small cached eval (~30 questions) on each PR
- [ ] Fail the build if F1 or faithfulness drops below threshold (leave a margin for LLM nondeterminism)
- [ ] Run the full eval manually or nightly

**Deployment**
- [ ] FastAPI service in Docker
- [ ] Simple UI showing the answer, citations, and the graph path used
- [ ] Add rate limiting
- [ ] Limit local request duration and concurrency so a public link can't overload the host machine
- [ ] Deploy to a public URL
- [ ] Record a 2-minute demo video

**Exit criterion:** public URL, demo video, green CI badge.

---

## Phase 8: Packaging (Week 8)

**README structure**
- [ ] Problem statement
- [ ] Results table (by hop count, with confidence intervals)
- [ ] Architecture diagram
- [ ] How to reproduce
- [ ] Failure gallery (5-10 real misses and why)
- [ ] Cost and latency
- [ ] Limitations

**Extras**
- [ ] Write a short blog post on what you learned, including negative results
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
- [ ] Results on both a public benchmark and your domain set, split by hop count
- [ ] At least four ablation variants with confidence intervals
- [ ] Hand-audited extraction and entity-resolution accuracy
- [ ] Traced, documented failure analysis
- [ ] One resume bullet backed by real numbers:

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
