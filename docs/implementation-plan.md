# Multi-Hop Agentic RAG with Evals: 8-Week Implementation Plan

**Goal:** Build an agentic multi-hop RAG system (graph + vector retrieval) with an evaluation, observability, and CI layer, deployed with a live demo. The finished project should support one resume bullet backed by real numbers.

**Assumed defaults (swap freely):**

| Item | Default |
|---|---|
| Corpus | 300-500 arXiv papers on one niche (e.g. LLM evaluation) |
| Language | Python |
| Graph + vectors | Neo4j (graph and native vector index in one store) |
| LLM | Any API (cheap model for extraction/planning, stronger for final answers) |
| Serving | FastAPI + Docker |
| Observability | Langfuse (or LangSmith) |
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

Every step traced (Langfuse) | cost/latency logged | eval suite gates CI
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

**Progress (2026-09-28):** BM25, pinned local dense embeddings, and BM25+dense RRF have been evaluated on the public MuSiQue slice. Supporting-document recall@5 is reported by hop count with paired bootstrap intervals in `eval/results/public_hybrid_v0.1.json`. A citation-constrained OpenAI Responses API evaluator now supports EM/F1, citation validation, token usage, latency, and optional cost estimates, but has not been run. Phase 2 remains in progress until answer metrics, calibrated faithfulness, cost/latency results, and a complete harness are reported.

---

## Phase 3: Graph Construction (Weeks 3-4)

**Schema and extraction**
- [ ] Define a constrained ontology
  - Entities: Paper, Method, Dataset, Metric, Task
  - Relations: PROPOSES, EVALUATES_ON, USES, OUTPERFORMS, CITES
- [ ] Extract triples per chunk with structured JSON output (cheaper model)
- [ ] Cache extraction results by chunk hash so re-runs are free
- [ ] Pilot on 20 documents, measure cost, extrapolate, then scale

**Entity resolution**
- [ ] Normalize names (case, punctuation, abbreviations)
- [ ] Find candidate duplicates via embedding similarity
- [ ] Adjudicate ambiguous pairs with an LLM
- [ ] Maintain an alias table
- [ ] Hand-label 100 pairs; report resolution precision and recall

**Storage and quality**
- [ ] Load into Neo4j; link every node and edge to its source chunk and document
- [ ] Hand-audit 50 random triples; record the accuracy
- [ ] Record total extraction cost and time

**Exit criterion:** graph loaded, with audit accuracy and extraction cost documented.

---

## Phase 4: Hybrid and Agentic Retrieval (Weeks 4-5)

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

**Exit criterion:** both retrievers run through the same eval harness.

---

## Phase 5: Ablations and Analysis (Week 6)

- [ ] Run all variants:
  - [ ] Vector-only
  - [ ] BM25 + vector
  - [ ] Graph-only
  - [ ] Fixed hybrid
  - [ ] Agentic
- [ ] Vary hop depth (1 vs 2) and top-k
- [ ] Produce tables and charts split by hop count
- [ ] Categorize 30-50 wrong answers by cause:
  - extraction miss
  - entity-resolution error
  - bad decomposition
  - expansion noise
  - generation error
- [ ] Document where GraphRAG does NOT help (negative results are strong interview material)

**Exit criterion:** a results section you can defend line by line.

---

## Phase 6: Observability, Cost, Guardrails (Weeks 6-7)

**Tracing**
- [ ] Trace every LLM and tool call in Langfuse, with tokens and cost per query
- [ ] Document one failure from symptom to root cause using a trace

**Cost control**
- [ ] Route cheap models to extraction and planning; stronger model to final answer
- [ ] Add caching
- [ ] Measure savings against an all-strong-model run

**Guardrails**
- [ ] Plant prompt-injection text in a few documents; verify the system ignores it
- [ ] Test abstention on the unanswerable set
- [ ] Enforce citation checks

**Exit criterion:** a documented traced failure, plus measured cost savings.

---

## Phase 7: CI and Deployment (Weeks 7-8)

**CI**
- [ ] GitHub Actions runs a small cached eval (~30 questions) on each PR
- [ ] Fail the build if F1 or faithfulness drops below threshold (leave a margin for LLM nondeterminism)
- [ ] Run the full eval manually or nightly

**Deployment**
- [ ] FastAPI service in Docker
- [ ] Simple UI showing the answer, citations, and the graph path used
- [ ] Add rate limiting
- [ ] Add a hard daily spend cap on the API key so a public link can't burn your budget
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
