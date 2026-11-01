# Implementation Roadmap: Research-Grade Agentic GraphRAG

> **Status:** Planning document — no code changes.
> **Generated:** 2026-11-01 from full repository inspection.
> **Scope:** Six workstreams across seven phases, taking the project from experimental to research-grade.

---

## Table of Contents

1. [Current Architecture Assessment](#section-1-current-architecture-assessment)
2. [Gap Analysis](#section-2-gap-analysis)
3. [Prioritized Roadmap](#section-3-prioritized-roadmap)
4. [File-Level Implementation Mapping](#section-4-file-level-implementation-mapping)
5. [Detailed Tasks and Acceptance Criteria](#section-5-detailed-tasks-and-acceptance-criteria)
6. [Experimental Research Design](#section-6-experimental-research-design)
7. [Technical Decisions](#section-7-technical-decisions)
8. [Risks and Mitigations](#section-8-risks-and-mitigations)
9. [Final Deliverables](#section-9-final-deliverables)
10. [Resume and Research Outcomes](#section-10-resume-and-research-outcomes)

---

## Section 1: Current Architecture Assessment

### 1.1 Current Architecture Summary

The system is a local-first, multi-hop research QA pipeline with three retrieval modalities (BM25, dense, graph), a bounded LLM planner agent, and citation-validated answer generation. All LLM inference runs through a loopback Ollama server with Qwen3 models. The codebase follows a flat module layout with CLI scripts orchestrated via `argparse`.

```
Question
  → Bounded Planner (Qwen3 4B, max 5 steps)
      ├─ keyword tool  → BM25 (retrieval/bm25.py)
      ├─ vector tool   → DenseRetriever (retrieval/dense.py)
      └─ graph tool    → GraphIndex BFS (retrieval/graph.py)
  → Answer Generator (Qwen3 8B)
  → Citation Validation
  → Cited answer or abstention
```

**Data flow:**
```
arXiv PDFs → ingest/ (download, extract, chunk)
  → data/processed/domain_passages.jsonl (10,878 passages, 500-word chunks, 75-word overlap)
  → graph/ (extract_domain_graph → merge → resolve_entity_candidates → audit_triples → load_neo4j)
  → data/processed/domain_graph_{nodes,edges}.jsonl
  → retrieval/ (BM25, dense, graph indexes loaded at query time)
  → agent/run_agent.py (planner loop → answer)
  → api/app.py (FastAPI, spawns agent as subprocess)
  → ui/index.html (vanilla HTML/JS, served from same origin)
```

### 1.2 Implemented Capabilities

| Component | File(s) | Status |
|---|---|---|
| BM25 retrieval (dependency-free Okapi) | `retrieval/bm25.py` (66 lines) | **Complete, tested on MuSiQue** |
| Dense retrieval (MiniLM-L6-v2, cached) | `retrieval/dense.py` (149 lines) | **Complete, tested** |
| RRF hybrid fusion | `retrieval/fusion.py` (14 lines) | **Complete** |
| In-memory graph index with BFS | `retrieval/graph.py` (164 lines) | **Complete, evaluated (underperforms)** |
| Fixed hybrid retriever (BM25+graph+dense RRF) | `retrieval/graph.py` `FixedHybridRetriever` | **Complete, evaluated** |
| Graph extraction (LLM-based, cached) | `graph/extract_domain_graph.py` (327 lines) | **Complete for 20-paper pilot** |
| Ontology with constrained schema | `graph/ontology.py` (107 lines) | **Complete** |
| Graph merge/consolidation | `graph/merge_graph_extractions.py` (159 lines) | **Complete** |
| Entity resolution candidate generation | `graph/resolve_entity_candidates.py` (163 lines) | **Complete (candidates only, no auto-merge)** |
| Triple audit worksheet + Wilson CI scoring | `graph/audit_triples.py` (128 lines) | **Complete (labels pending)** |
| Neo4j loader (idempotent MERGE) | `graph/load_neo4j.py` (145 lines) | **Dry-run tested only** |
| Bounded agentic planner (5 steps, 3 tools) | `agent/run_agent.py` (340 lines) | **Complete, 3-question pilot** |
| Ollama client (loopback-only, stdlib) | `src/agentic_graphrag/local_llm.py` (120 lines) | **Complete** |
| MuSiQue 300-question public benchmark | `eval/data/public/` | **Frozen** |
| 109-question domain benchmark (98 answerable + 11 unanswerable) | `eval/data/domain/` | **Frozen** |
| Retrieval eval (BM25, dense, hybrid, graph) | `eval/run_hybrid_eval.py`, `eval/run_graph_eval.py` | **Complete with bootstrap CIs** |
| Answer eval (EM, F1, citation, latency) | `eval/run_answer_eval.py`, `eval/answer_metrics.py` | **Complete** |
| Agent eval harness | `eval/run_agent_eval.py` | **Complete (3-question pilot)** |
| Prompt injection smoke test (5 cases) | `eval/run_prompt_injection_eval.py` | **Complete, all passed** |
| Unanswerable abstention eval | eval scripts + `questions_unanswerable_v1.0.jsonl` | **Complete (7/11 abstained)** |
| Results report builder | `eval/build_results_report.py` | **Complete** |
| CI quality gate (BM25 recall floors) | `.github/workflows/retrieval-eval.yml` | **Complete** |
| FastAPI backend | `api/app.py` (258 lines) | **Scaffold complete, not browser-tested** |
| Static UI | `ui/index.html` (153 lines) | **Scaffold complete, not browser-tested** |
| Smoke pipeline | `src/agentic_graphrag/pipeline.py` (109 lines) | **Complete** |
| Config management | `configs/default.toml` (61 lines) | **Complete** |
| Corpus ingestion pipeline | `ingest/*.py` (7 scripts) | **Complete for 325 papers** |

### 1.3 Partially Implemented Capabilities

1. **Knowledge graph quality audit:** The 50-row audit worksheet is generated but **human labels are pending**. No triple accuracy score exists yet.
2. **Entity resolution:** 307 embedding-ranked candidate pairs are generated with `UNREVIEWED` status. No LLM or human adjudication has been performed. 103 alias collisions remain unresolved.
3. **Neo4j integration:** The loader (`graph/load_neo4j.py`) passes dry-run validation but has **never been run against a live database**. Neo4j is not used by any retrieval path.
4. **Agent evaluation:** Only a 3-question wiring pilot exists. No systematic agent evaluation has been performed.
5. **Answer quality:** Token F1 of 0.287 on domain, 0.216 on public (stratified 30). EM is 0.000 on domain. Faithfulness judging is not implemented.

### 1.4 Technical Debt

1. **`read_jsonl()` duplicated in 8+ files** — `agent/run_agent.py`, `graph/extract_domain_graph.py`, `graph/merge_graph_extractions.py`, `graph/resolve_entity_candidates.py`, `graph/audit_triples.py`, `graph/load_neo4j.py`, `eval/run_hybrid_eval.py`, `eval/run_answer_eval.py`.
2. **`sys.path` manipulation** in every script (`REPOSITORY_ROOT` pattern) instead of proper package imports.
3. **Hash truncation inconsistency:** Most IDs use `sha256[:20]`, but `load_neo4j.py` evidence IDs use `[:24]`, and `pipeline.py` uses `[:16]`.
4. **No automated tests:** The `tests/` directory does not exist. All validation is through eval scripts.
5. **No `__pycache__` in `.gitignore` verification** — compiled bytecode files are present in the tree.
6. **API spawns agent as subprocess** (`api/app.py` L150-257) rather than in-process, adding overhead and limiting error handling.

### 1.5 Existing Bottlenecks

1. **Graph retrieval quality:** Graph-only recall@5 = 0.041 on domain (vs BM25 0.549). Adding graph to BM25 via RRF *hurts* recall (0.435 vs 0.549). This is the single most important gap.
2. **Graph coverage:** Only 197/10,878 passages (1.8%) have been processed for graph extraction. The pilot covers 20 of 325 papers.
3. **Entity linking weakness:** Graph seeding uses BM25 over entity names/aliases — a crude method that misses entities with different surface forms. Dense entity seeding scored even worse (0.024 recall@5).
4. **Answer quality:** EM 0.000 on domain, F1 0.287. The 4B planner occasionally generates too-short queries, triggering fallback to the original question.
5. **Abstention unreliability:** Only 7/11 unanswerable probes result in abstention. 4 unsupported answers are produced.
6. **Local inference latency:** Agent end-to-end takes 77.4s (vs 14.4s for BM25 answer generation). Embedding cache build takes ~14 minutes.

### 1.6 Architectural Strengths to Preserve

1. **Local-first design:** Loopback-only Ollama client with proxy bypass, redirect prevention, and explicit privacy safeguards.
2. **Constrained ontology:** Five entity types, five predicates with typed endpoint rules — well-defined and enforced at extraction time.
3. **Evidence provenance:** Every graph edge links to source_chunk_id and paper_id. Nodes track source_chunk_ids and paper_ids.
4. **Deterministic evaluation:** SHA-256 checksums on all inputs, seeded bootstrap resampling, frozen question sets, pinned model revisions.
5. **Honest negative results:** The project documents that graph retrieval underperforms BM25 and does not hide this.
6. **Zero external dependencies for core retrieval:** BM25 is stdlib-only. Dense and graph are optional installs.
7. **Structured output with JSON schemas:** Both planner and answer models use constrained JSON output with retry budgets.
8. **Citation validation:** Invalid citations trigger forced abstention — a strong safety mechanism.

---

## Section 2: Gap Analysis

| # | Component | Current State | Identified Gap | Proposed Improvement | Priority |
|---|---|---|---|---|---|
| 1 | Triple accuracy audit | Partially implemented — worksheet generated, labels pending | No measured accuracy; graph quality unknown | Complete 50-row human audit; compute Wilson CI; establish accuracy baseline | P0 |
| 2 | Entity resolution | Partially implemented — 307 candidates generated, all UNREVIEWED | 103 alias collisions unresolved; duplicate entities inflate graph noise | Adjudicate candidates; merge confirmed duplicates; measure resolution precision | P0 |
| 3 | Graph coverage | Partially implemented — 197/10,878 passages (20/325 papers) | 98.2% of corpus has no graph representation | Scale extraction after audit validates quality; extract remaining papers in batches | P1 |
| 4 | Graph retrieval quality | Implemented but underperforming — recall@5 = 0.041 | Entity linking is crude (BM25 over names); BFS score decay (0.5/hop) is aggressive; no relation-aware traversal | Improve entity linking; tune score decay; experiment with relation-aware traversal | P0 |
| 5 | Query-to-entity linking | Implemented — BM25 over entity name+aliases | Misses entities with different surface forms; dense seeding scored worse (0.024) | Hybrid entity linking with alias expansion, fuzzy matching, LLM-assisted disambiguation | P0 |
| 6 | Reranking | Not implemented | Retrieved passages are ranked only by BM25/RRF scores; no semantic reranking | Add cross-encoder or lightweight reranker after fusion | P1 |
| 7 | Query classification | Not implemented | Agent treats all questions identically; planner decides tools without query analysis | Classify query type (single-hop, multi-hop, comparison, broad); route accordingly | P1 |
| 8 | Query decomposition | Partially implemented — planner generates sub-queries | No explicit decomposition; planner generates one query per step reactively | Add structured decomposition before tool selection for multi-hop questions | P1 |
| 9 | Evidence sufficiency detection | Partially implemented — planner can "finish" | No principled stopping criterion; relies on planner judgment | Add confidence/coverage heuristics to supplement planner decision | P2 |
| 10 | Faithfulness evaluation | Not implemented | No judge for whether answers are faithful to retrieved evidence | Add LLM-as-judge faithfulness metric calibrated against human labels | P1 |
| 11 | nDCG / MRR metrics | Not implemented | Only supporting-document recall@k is measured | Add MRR and nDCG for richer retrieval quality signal | P2 |
| 12 | Answer relevance metric | Not implemented | EM and token F1 are coarse; no semantic similarity metric | Add BERTScore or LLM-judged answer relevance | P2 |
| 13 | Tool selection accuracy | Not implemented | No measurement of whether planner picks the right tool | Annotate subset with ideal tool; measure tool selection accuracy | P2 |
| 14 | Unit tests | Not implemented — no `tests/` directory | No regression protection for core modules | Add pytest tests for BM25, dense, graph, ontology, answer_metrics, fusion | P0 |
| 15 | Docker packaging | Not implemented | No reproducible deployment; relies on local Python setup | Dockerfile + docker-compose with Ollama | P1 |
| 16 | Graph visualization | Not implemented | No way to inspect graph structure or traversal paths | Interactive graph explorer with highlighted paths | P2 |
| 17 | Agent trace visualization | Not implemented | Agent steps are JSON blobs; no visual timeline | Agent execution timeline in UI | P2 |
| 18 | Evidence explorer UI | Not implemented | UI shows only answer + citation IDs; no passage inspection | Show retrieved passages, link to papers, explain selection | P1 |
| 19 | API/UI browser testing | Not implemented — "has not been exercised in a browser" (ui/README.md) | Unknown whether the UI actually works | Run API + UI in browser; fix issues | P0 |
| 20 | Shared utility module | Not implemented — `read_jsonl` duplicated 8× | Maintenance burden; inconsistency risk | Extract shared I/O utilities to `src/agentic_graphrag/io.py` | P1 |
| 21 | Confidence-weighted traversal | Partially implemented — confidence used in score but with fixed 0.5 decay | Score decay is aggressive and not tuned | Experiment with different decay functions; use calibrated confidence | P1 |
| 22 | High-degree node handling | Not implemented | Hub entities (e.g., "transformer") could dominate BFS expansion | Add degree-based damping or neighbor pruning | P2 |
| 23 | Reproducible experiment configs | Partially implemented — TOML config exists but experiments use CLI overrides | Hard to reproduce exact experiment settings | Save experiment config snapshots alongside results | P1 |
| 24 | Statistical significance testing | Partially implemented — bootstrap CIs exist | No paired permutation tests; no multiple-comparison correction | Add paired bootstrap tests for all ablation comparisons | P2 |
| 25 | Corpus rights review | Not implemented | Legal status of PDF corpus unknown | Document fair use / licensing status before public deployment | P1 |

---

## Section 3: Prioritized Roadmap

### Phase 0 — Repository Audit and Reproducibility (Est. 3–5 days)

**Objective:** Establish the actual state of the repository, add regression protection, and verify the existing system runs end-to-end.

**Why first:** Every subsequent phase depends on being able to run existing code reliably and detect regressions. The UI/API have never been browser-tested.

### Phase 1 — Knowledge Graph Quality Audit (Est. 5–8 days)

**Objective:** Validate entity extraction, relationships, entity resolution, and graph quality so that subsequent graph retrieval improvements are built on trustworthy data.

**Why second:** Graph retrieval underperforms because the graph itself may be unreliable. Improving retrieval algorithms on an unaudited graph wastes effort.

### Phase 2 — Graph Retrieval Improvements (Est. 8–12 days)

**Objective:** Make graph retrieval measurably useful for multi-hop questions by improving entity linking, traversal, scoring, and fusion.

**Why third:** This is the core research question. It depends on Phase 1 producing a validated graph.

### Phase 3 — Adaptive Agent (Est. 6–8 days)

**Objective:** Transform the bounded planner into an adaptive retrieval agent with query classification, decomposition, and intelligent routing.

**Why fourth:** Adaptive routing benefits from knowing which retrieval modalities work (Phase 2 experiments).

### Phase 4 — Evaluation and Research Validation (Est. 5–7 days)

**Objective:** Run comprehensive baselines, ablations, and statistical analysis. Add missing evaluation metrics.

**Why fifth:** Full evaluation should run after retrieval and agent improvements are in place to produce meaningful comparisons.

### Phase 5 — Visual Evidence Explorer (Est. 5–8 days)

**Objective:** Build a research-oriented UI with graph visualization, evidence inspection, and agent traces.

**Why sixth:** Visualization is most valuable after the graph is validated and retrieval is improved.

### Phase 6 — Packaging and Documentation (Est. 4–6 days)

**Objective:** Dockerize, add CI, finalize documentation, and prepare demonstration materials.

**Why last:** Packaging should wrap a working, validated system.

---


## Section 4: File-Level Implementation Mapping

### Phase 0 — Repository Audit and Reproducibility

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 0.1 Extract shared I/O utilities | `agent/run_agent.py`, `graph/*.py`, `eval/*.py` (all contain `read_jsonl`) | `src/agentic_graphrag/io.py` | `read_jsonl()`, `write_jsonl()`, `sha256_file()` | None | `tests/test_io.py` |
| 0.2 Add unit tests for core modules | `retrieval/bm25.py`, `retrieval/dense.py`, `retrieval/graph.py`, `retrieval/fusion.py`, `graph/ontology.py`, `eval/answer_metrics.py` | `tests/test_bm25.py`, `tests/test_dense.py`, `tests/test_graph.py`, `tests/test_fusion.py`, `tests/test_ontology.py`, `tests/test_answer_metrics.py`, `tests/conftest.py` | All public functions | pytest (dev dependency) | Self — these ARE the tests |
| 0.3 Browser-test API + UI | `api/app.py`, `ui/index.html` | None (may need bug fixes in existing files) | `local_resources_ready()`, `/ask` endpoint, JS `fetch` handler | FastAPI, uvicorn, Ollama running | Manual browser test; optionally `tests/test_api.py` |
| 0.4 Verify end-to-end pipeline | `setup_corpus.ps1`, `agent/run_agent.py` | `docs/QUICKSTART.md` | `main()` in agent | All data files present, Ollama running | Run agent on 1 question, verify JSON output |
| 0.5 Add pyproject.toml dev dependencies | `pyproject.toml` | None (modify existing) | N/A | pytest, ruff (optional) | `pip install -e ".[dev]"` succeeds |
| 0.6 Standardize sys.path handling | All scripts with `REPOSITORY_ROOT` pattern | None (modify existing) | N/A | Package installed in editable mode | All scripts importable without sys.path hacks |

### Phase 1 — Knowledge Graph Quality Audit

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 1.1 Complete triple audit labels | `graph/audit_triples.py`, `data/processed/triple_audit_v1.0.jsonl` | None (modify data file) | `score_audit()` | Human reviewer | Re-run `score_audit()`; verify Wilson CI |
| 1.2 Entity resolution adjudication | `graph/resolve_entity_candidates.py`, `data/processed/entity_resolution_candidates.jsonl` | `graph/apply_entity_resolution.py` | `apply_merges()`, `update_graph_files()` | Adjudicated candidate decisions | `tests/test_entity_resolution.py` |
| 1.3 LLM-assisted entity disambiguation | `graph/resolve_entity_candidates.py` | `graph/llm_disambiguate_entities.py` | `disambiguate_pair()`, `batch_disambiguate()` | `local_llm.py`, Ollama | `tests/test_llm_disambiguate.py` |
| 1.4 Alias collision resolution | `graph/merge_graph_extractions.py` (outputs `domain_graph_alias_collisions.jsonl`) | None (modify merge or add resolver) | `resolve_collisions()` | Entity resolution results | Collision count drops to 0 |
| 1.5 Graph quality metrics dashboard | `graph/audit_triples.py` | `graph/graph_quality_report.py` | `compute_quality_metrics()` | Audit labels, entity resolution results | `tests/test_graph_quality.py` |
| 1.6 Extraction prompt improvements | `graph/extract_domain_graph.py` (prompt at L160-172) | None (modify existing) | Prompt text in `main()` | Ollama | Re-run extraction on pilot; compare acceptance rate |
| 1.7 Scale extraction to full corpus | `graph/extract_domain_graph.py` | None (adjust CLI parameters) | `select_pilot_papers()` bypass for full run | Validated extraction quality | Extraction summary stats |

### Phase 2 — Graph Retrieval Improvements

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 2.1 Improved entity linking | `retrieval/graph.py` `seed_entities()` (L54-57) | `retrieval/entity_linker.py` | `EntityLinker.link()`, `fuzzy_match()`, `alias_expand()` | `graph/ontology.py`, embeddings | `tests/test_entity_linker.py` |
| 2.2 Relation-aware traversal | `retrieval/graph.py` `expand()` (L59-116) | None (modify existing) | Modified `expand()` with predicate filtering | Ontology | `tests/test_graph.py` extended |
| 2.3 Confidence-weighted scoring tuning | `retrieval/graph.py` L108 (hardcoded `0.5` decay) | `configs/default.toml` (add `score_decay` param) | `expand()` decay logic | Config | Ablation experiments |
| 2.4 Adaptive hop depth | `retrieval/graph.py` L106 (fixed `hops` param) | None (modify existing) | Add query-dependent hop selection | Query classifier (Phase 3) | `tests/test_graph.py` extended |
| 2.5 High-degree node damping | `retrieval/graph.py` `expand()` | None (modify existing) | Degree-based score penalty in BFS | Graph statistics | `tests/test_graph.py` extended |
| 2.6 Cross-encoder reranking | None | `retrieval/rerank.py` | `CrossEncoderReranker.rerank()` | `sentence-transformers` or `cross-encoder` model | `tests/test_rerank.py` |
| 2.7 Graph-passage expansion | `retrieval/graph.py` | None (modify existing) | Expand retrieved entities to neighboring passages | Graph index | Retrieval eval comparison |
| 2.8 Alternative fusion strategies | `retrieval/fusion.py` (14 lines, RRF only) | None (extend existing) | `weighted_rrf()`, `combSUM()`, `combMNZ()` | None | `tests/test_fusion.py` extended |

### Phase 3 — Adaptive Agent

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 3.1 Query intent classifier | `agent/run_agent.py` | `agent/query_classifier.py` | `classify_query()` → single-hop / multi-hop / comparison / broad | `local_llm.py` or heuristic | `tests/test_query_classifier.py` |
| 3.2 Query decomposition | `agent/run_agent.py` (planner generates sub-queries reactively) | `agent/query_decomposer.py` | `decompose()` → list of sub-questions | `local_llm.py` | `tests/test_query_decomposer.py` |
| 3.3 Adaptive tool routing | `agent/run_agent.py` L205-218 (fixed tool dispatch) | None (modify existing) | Routing logic in planner loop | Query classifier, retrieval experiments | Routing accuracy measurement |
| 3.4 Evidence sufficiency detection | `agent/run_agent.py` L240-242 (context_budget check) | `agent/sufficiency.py` | `is_sufficient()` | Retrieved passages, question | `tests/test_sufficiency.py` |
| 3.5 Retrieval failure recovery | `agent/run_agent.py` L198-201 (stops on repeated tool/query) | None (modify existing) | Fallback to alternative tool on empty results | Agent loop | Agent eval with failure cases |
| 3.6 Iterative retrieval refinement | `agent/run_agent.py` | None (modify existing) | Use prior step results to refine next query | Agent loop | Agent eval comparison |

### Phase 4 — Evaluation and Research Validation

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 4.1 Add MRR and nDCG metrics | `eval/run_hybrid_eval.py` `summarize()` (L70-111) | None (modify existing + `eval/answer_metrics.py`) | `mrr()`, `ndcg()` | None | `tests/test_answer_metrics.py` extended |
| 4.2 Faithfulness judge | None | `eval/faithfulness_judge.py` | `judge_faithfulness()`, `calibrate_judge()` | `local_llm.py`, 50 human-labeled answers | `tests/test_faithfulness.py` |
| 4.3 Comprehensive agent evaluation | `eval/run_agent_eval.py` (3-question pilot) | None (run with larger `--per-hop`) | `main()` with `--per-hop 10` | All data + Ollama | Agent metrics comparison |
| 4.4 Component ablation suite | `eval/run_graph_eval.py` (already has many variants) | `eval/run_ablation_suite.py` | `run_all_ablations()` | All retrieval modules | Per-ablation result files |
| 4.5 Error categorization | None | `eval/categorize_errors.py` | `categorize_error()` → extraction_miss / resolution_error / decomposition / noise / generation | Human-labeled subset | Error category distribution |
| 4.6 Experiment config snapshots | `configs/default.toml` | `eval/save_experiment_config.py` | `snapshot_config()` | None | Config hash matches result input |
| 4.7 Answer quality on additional benchmarks | `eval/download_public_data.py` | `eval/prepare_hotpotqa.py` (if needed) | HotpotQA / 2WikiMultiHop data prep | Downloaded data | Retrieval eval on new benchmark |

### Phase 5 — Visual Evidence Explorer

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 5.1 Evidence explorer panel | `ui/index.html` (153 lines), `api/app.py` | Extend `ui/index.html` or create `ui/explorer.html` | JS: `renderPassages()`, `linkToPaper()` | API response with passage text | Manual browser test |
| 5.2 Agent execution timeline | `ui/index.html` (L132-145 shows steps) | Extend existing | JS: `renderTimeline()` | API response with step details | Manual browser test |
| 5.3 Knowledge graph visualization | None | `ui/graph.html` or extend `ui/index.html` | JS: graph rendering with D3.js or Cytoscape.js | API endpoint for subgraph data | Manual browser test |
| 5.4 Graph subgraph API endpoint | `api/app.py` | None (extend existing) | `GET /graph/subgraph?entity_id=...` | Graph data files | `tests/test_api.py` |
| 5.5 Retrieval comparison dashboard | None | `ui/dashboard.html` | JS: `renderComparison()`, chart rendering | Eval result JSON files | Manual browser test |
| 5.6 API response enrichment | `api/app.py` L150-257 | None (modify existing) | Add passage text, graph paths to response | Agent output enrichment | API response schema test |

### Phase 6 — Packaging and Documentation

| Task | Existing Files | New Files | Key Functions/Classes | Dependencies | Tests Needed |
|---|---|---|---|---|---|
| 6.1 Dockerfile | None | `Dockerfile` | N/A | Python 3.11, pip | `docker build` succeeds |
| 6.2 Docker Compose with Ollama | None | `docker-compose.yml` | N/A | Docker, Ollama image | `docker compose up` starts system |
| 6.3 Environment variable management | `.env.example` | `.env.example` updated | N/A | None | All vars documented |
| 6.4 CI expansion | `.github/workflows/retrieval-eval.yml` | `.github/workflows/test.yml` | N/A | pytest, GitHub Actions | CI passes on clean checkout |
| 6.5 Architecture diagrams | `README.md` (has Mermaid flowchart) | `docs/architecture.md` | N/A | None | Diagrams render correctly |
| 6.6 Benchmark report documentation | `eval/results-summary.md` | `docs/BENCHMARK_REPORT.md` | N/A | Eval results | Report matches result JSONs |
| 6.7 Demonstration video | None | `docs/demo-script.md` | N/A | Working system | Video recorded |
| 6.8 Complete README | `README.md` (85 lines) | None (extend existing) | N/A | All phases complete | README covers all sections |

---

## Section 5: Detailed Tasks and Acceptance Criteria

### Phase 0 — Repository Audit and Reproducibility

**Objective:** Verify the system works end-to-end, add regression protection, and clean up technical debt.

#### Task 0.1: Extract Shared I/O Utilities
- **Technical approach:** Create `src/agentic_graphrag/io.py` with `read_jsonl()`, `write_jsonl()`, `sha256_file()`. Update all 8+ files that duplicate these functions to import from the shared module.
- **Expected outputs:** Single source of truth for I/O utilities.
- **Dependencies:** None.
- **Tests:** `tests/test_io.py` — round-trip JSONL read/write, empty file, malformed line handling.
- **Acceptance criteria:** `grep -r "def read_jsonl" .` returns only `src/agentic_graphrag/io.py`.
- **Definition of done:** All scripts use shared utilities; all existing eval results are unchanged.
- **Priority:** P1 | **Complexity:** Low | **Effort:** 0.5 days

#### Task 0.2: Add Unit Tests for Core Modules
- **Technical approach:** Add `pytest` to `[project.optional-dependencies]` as `dev = ["pytest>=8,<9"]`. Create `tests/` directory with test files for BM25, dense retriever, graph index, RRF fusion, ontology, and answer metrics.
- **Expected outputs:** ≥80% line coverage on core retrieval and evaluation modules.
- **Dependencies:** Task 0.1 (shared utilities).
- **Tests:**
  - `test_bm25.py`: tokenize, search ranking, edge cases (single doc, no matches, k>corpus).
  - `test_graph.py`: seed_entities, expand with known graph, hop limits, max_nodes limits, empty graph.
  - `test_fusion.py`: RRF with known rankings, single ranking, empty ranking.
  - `test_ontology.py`: normalize_name, stable_entity_id, extraction_records with valid/invalid inputs, ALLOWED_ENDPOINTS coverage.
  - `test_answer_metrics.py`: exact_match, token_f1, citation_metrics, normalize_answer.
- **Acceptance criteria:** `pytest tests/` passes with 0 failures; all public functions in core modules have ≥1 test.
- **Definition of done:** CI can run `pytest tests/` as a quality gate.
- **Priority:** P0 | **Complexity:** Medium | **Effort:** 2 days

#### Task 0.3: Browser-Test API and UI
- **Technical approach:** Install `api` optional dependencies. Start Ollama with required models. Run `uvicorn api.app:app --host 127.0.0.1`. Open `http://127.0.0.1:8000/` in browser. Submit a question. Verify response renders.
- **Expected outputs:** Confirmed working UI with screenshot evidence. List of any bugs found and fixed.
- **Dependencies:** Ollama running, models pulled, data files present.
- **Tests:** Manual browser test with at least 3 different questions.
- **Acceptance criteria:** UI renders answer, citations, and agent steps without JavaScript errors. API returns valid JSON for `/healthz` and `/ask`.
- **Definition of done:** `ui/README.md` updated to remove "has not yet been exercised in a browser" caveat.
- **Priority:** P0 | **Complexity:** Low | **Effort:** 1 day

#### Task 0.4: Verify End-to-End Pipeline Reproducibility
- **Technical approach:** On a clean checkout, follow README instructions to run the smoke pipeline, retrieval eval, and agent on 1 question. Document any missing steps.
- **Expected outputs:** Updated `docs/QUICKSTART.md` with verified step-by-step instructions.
- **Dependencies:** All tools installed.
- **Tests:** Clean checkout reproduces BM25 recall@5 = 0.429 on public MuSiQue.
- **Acceptance criteria:** A new developer can follow the guide and get a working system in <30 minutes (excluding model downloads).
- **Definition of done:** `QUICKSTART.md` merged and tested by a second person or on a fresh environment.
- **Priority:** P0 | **Complexity:** Low | **Effort:** 1 day

#### Task 0.5: Add Dev Dependencies and Linting
- **Technical approach:** Add `dev = ["pytest>=8,<9", "ruff>=0.7"]` to `pyproject.toml`. Add `[tool.ruff]` section with line-length=120.
- **Expected outputs:** `pip install -e ".[dev]"` installs all development tools.
- **Dependencies:** None.
- **Acceptance criteria:** `ruff check .` and `pytest tests/` both pass.
- **Priority:** P1 | **Complexity:** Low | **Effort:** 0.5 days

---

### Phase 1 — Knowledge Graph Quality Audit

**Objective:** Validate the knowledge graph so that retrieval improvements are built on trustworthy data.

#### Task 1.1: Complete Triple Audit Labels
- **Technical approach:** Open `data/processed/triple_audit_v1.0.jsonl`. For each of the 50 sampled edges, read the `passage_text` and determine whether the triple (subject → predicate → object) is explicitly supported. Set `reviewer_correct` to `true` or `false`. Add `reviewer_notes` for ambiguous cases. Run `python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl`.
- **Expected outputs:** `triple_audit_summary.json` with `triple_accuracy`, `wilson_95_ci`, `sample_size`.
- **Dependencies:** None (audit worksheet already generated).
- **Tests:** `score_audit()` returns valid summary with `sample_size=50`.
- **Acceptance criteria:** Triple accuracy is measured with 95% Wilson CI. If accuracy < 0.70, extraction prompts must be improved before scaling.
- **Definition of done:** Audit summary committed to `eval/results/triple_audit_v1.0_summary.json`.
- **Priority:** P0 | **Complexity:** Low (human effort, not coding) | **Effort:** 2 days

#### Task 1.2: Entity Resolution Adjudication
- **Technical approach:** Review the 307 candidate pairs in `data/processed/entity_resolution_candidates.jsonl`. For each pair, set `decision` to `MERGE`, `KEEP_SEPARATE`, or `UNCERTAIN`. For `MERGE` decisions, set `canonical_entity_id` to the preferred ID. Create `graph/apply_entity_resolution.py` that reads adjudicated decisions and rewrites node/edge files.
- **Expected outputs:** Adjudicated candidates file. Entity resolution precision and recall (on the adjudicated set). Reduced node count after merging confirmed duplicates.
- **Dependencies:** Task 1.1 (audit should complete first to understand extraction quality).
- **Tests:** `tests/test_entity_resolution.py` — merge operation preserves all source_chunk_ids, aliases, paper_ids; merged node has union of provenance.
- **Acceptance criteria:** All 307 candidates reviewed. Merge precision ≥ 0.90 (no incorrect merges). Alias collision count reduced by ≥50%.
- **Definition of done:** Merged graph files committed. Resolution accuracy documented.
- **Priority:** P0 | **Complexity:** Medium | **Effort:** 3 days

#### Task 1.3: LLM-Assisted Entity Disambiguation (Optional)
- **Technical approach:** For pairs where embedding similarity is high but human judgment is uncertain, use Qwen3 4B to compare entity descriptions in context. Create `graph/llm_disambiguate_entities.py` with structured output (MERGE/KEEP_SEPARATE/UNCERTAIN + reason).
- **Expected outputs:** LLM disambiguation results for uncertain pairs. Comparison of LLM vs human agreement rate.
- **Dependencies:** Task 1.2 (human labels as ground truth for calibration).
- **Tests:** Agreement rate with human labels on a held-out set.
- **Acceptance criteria:** LLM agreement with human labels ≥ 0.85 on a 30-pair calibration set.
- **Definition of done:** LLM disambiguation tool available for future extraction batches.
- **Priority:** P2 | **Complexity:** Medium | **Effort:** 2 days

#### Task 1.4: Extraction Prompt Improvement
- **Technical approach:** Analyze the 726 rejected triples from the pilot. Categorize rejection reasons: wrong endpoint types, missing entities, out-of-range confidence, ambiguous aliases. Adjust the extraction prompt in `graph/extract_domain_graph.py` (L160-172) to reduce common error patterns. Re-run on a 20-passage validation set and compare acceptance rates.
- **Expected outputs:** Improved prompt version (`domain-graph-extraction-local-v3`). Acceptance rate comparison (v2 vs v3).
- **Dependencies:** Task 1.1 (understand current quality first).
- **Tests:** Re-run extraction on same 20 passages; compare triple counts and acceptance rate.
- **Acceptance criteria:** Triple acceptance rate improves by ≥10 percentage points (current: 636/1362 = 46.7%) without reducing accuracy.
- **Definition of done:** New prompt version documented. Before/after comparison in `graph/README.md`.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 1.5: Scale Extraction to Full Corpus
- **Technical approach:** After audit validates quality and prompt improvements are applied, run `extract_domain_graph.py` on all 325 papers (10,878 passages). Use the existing caching mechanism to avoid re-processing the pilot passages. Run in batches of 50 papers with progress monitoring.
- **Expected outputs:** Complete graph covering all 325 papers. Updated node/edge/alias files. Extraction summary with entity/triple counts.
- **Dependencies:** Tasks 1.1, 1.2, 1.4 (quality must be validated first).
- **Tests:** Merge and validation succeed. Node/edge counts increase proportionally.
- **Acceptance criteria:** ≥90% of passages successfully processed. Acceptance rate ≥ prompt v3 baseline.
- **Definition of done:** Full graph files committed. Extraction cost/time documented.
- **Priority:** P1 | **Complexity:** Low (operational, not algorithmic) | **Effort:** 2-3 days (wall-clock; ~16s/passage = ~48 hours compute)

#### Task 1.6: Graph Quality Metrics Report
- **Technical approach:** Create `graph/graph_quality_report.py` that computes: entity count by type, edge count by predicate, mean/median node degree, provenance coverage (% of edges with source_chunk_id), alias collision rate, duplicate node rate (post-resolution), triple accuracy (from audit), entity resolution precision.
- **Expected outputs:** `data/processed/graph_quality_report.json` with all metrics.
- **Dependencies:** Tasks 1.1, 1.2, 1.5.
- **Tests:** `tests/test_graph_quality.py` — metric computation on a small synthetic graph.
- **Acceptance criteria:** All metrics computed and documented. Provenance coverage = 100% (by design of extraction pipeline).
- **Definition of done:** Quality report committed and referenced from `graph/README.md`.
- **Priority:** P1 | **Complexity:** Low | **Effort:** 1 day

---

### Phase 2 — Graph Retrieval Improvements

**Objective:** Make graph retrieval measurably useful for multi-hop research questions.

#### Task 2.1: Diagnose Graph Retrieval Underperformance
- **Technical approach:** Analyze the 98 domain questions where graph recall@5 = 0.041. For each question, check: (a) does the graph contain relevant entities? (b) does `seed_entities()` find them? (c) does BFS reach passages containing gold answers? (d) where does the pipeline break? Categorize failures into: entity not in graph, entity linking failure, traversal failure, scoring failure.
- **Expected outputs:** Diagnostic report with failure category distribution.
- **Dependencies:** Phase 1 (audited graph).
- **Tests:** Diagnostic script produces categorized output.
- **Acceptance criteria:** ≥80% of graph retrieval failures have an identified root cause.
- **Definition of done:** Diagnostic report in `docs/graph_retrieval_diagnosis.md`.
- **Priority:** P0 | **Complexity:** Medium | **Effort:** 2 days

#### Task 2.2: Improved Entity Linking
- **Technical approach:** Replace the current BM25-over-names entity seeding (`retrieval/graph.py` L54-57) with a hybrid linker that:
  1. Normalizes the query (lowercase, remove punctuation).
  2. Extracts entity mentions from the query using NER or pattern matching.
  3. Fuzzy-matches mentions against the alias table (edit distance, Jaccard).
  4. Optionally uses dense embeddings over entity descriptions.
  5. Falls back to BM25 over names+aliases if no exact/fuzzy match.
- **Expected outputs:** `retrieval/entity_linker.py` with `EntityLinker` class. Improved seed entity precision on domain questions.
- **Dependencies:** Phase 1 (clean alias table).
- **Tests:** `tests/test_entity_linker.py` — known queries map to correct entities.
- **Acceptance criteria:** Entity linking precision ≥ 0.50 on a 30-question annotated subset (current BM25 seeding is unmeasured but produces 0.041 recall).
- **Definition of done:** Entity linker integrated into `GraphIndex`. Retrieval eval shows measurable improvement.
- **Priority:** P0 | **Complexity:** High | **Effort:** 3 days

#### Task 2.3: Relation-Aware Traversal
- **Technical approach:** Modify `GraphIndex.expand()` to consider predicate types during BFS. For example, when traversing from a Method entity looking for evaluation results, prioritize EVALUATES_ON edges over CITES edges. Add an optional `predicate_weights` parameter to `expand()`.
- **Expected outputs:** Modified `expand()` with predicate-aware scoring. Comparison of relation-aware vs relation-agnostic traversal.
- **Dependencies:** Task 2.1 (understand failure modes).
- **Tests:** `tests/test_graph.py` extended with predicate-weighted traversal tests.
- **Acceptance criteria:** Experiment shows relation-aware traversal differs from baseline (positive or negative — both are valid findings).
- **Definition of done:** Ablation results documented. Decision on whether to enable by default.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 2.4: Score Decay and Confidence Tuning
- **Technical approach:** The current BFS uses a fixed `0.5` decay per hop (`retrieval/graph.py` L108: `next_score = current_score * confidence * 0.5`). Parameterize this decay factor and run a grid search over `{0.3, 0.5, 0.7, 0.9}` on the domain evaluation set. Also experiment with using calibrated confidence scores instead of raw extraction confidence.
- **Expected outputs:** Optimal decay factor for domain corpus. Sensitivity analysis.
- **Dependencies:** Phase 1 (audited confidence scores).
- **Tests:** Grid search runner produces per-setting recall values.
- **Acceptance criteria:** Best decay setting identified. If improvement > 2 percentage points in recall@5, update default config.
- **Definition of done:** Results documented. Config updated if beneficial.
- **Priority:** P1 | **Complexity:** Low | **Effort:** 1 day

#### Task 2.5: High-Degree Node Damping
- **Technical approach:** Compute degree distribution of the graph. Identify hub nodes (e.g., "transformer", "attention", "BERT" likely have very high degree). Add a degree-based damping factor to BFS: `damping = 1 / (1 + log(degree))` applied to neighbor scores. Compare with and without damping.
- **Expected outputs:** Degree distribution analysis. Damping experiment results.
- **Dependencies:** Phase 1 (complete graph).
- **Tests:** `tests/test_graph.py` — damping reduces score for high-degree neighbors.
- **Acceptance criteria:** Experiment produces measurable comparison. If damping hurts recall, document and disable.
- **Definition of done:** Decision documented with experimental evidence.
- **Priority:** P2 | **Complexity:** Low | **Effort:** 1 day

#### Task 2.6: Cross-Encoder Reranking
- **Technical approach:** After fusion produces a candidate set (top 20-50), apply a cross-encoder model to re-score (query, passage) pairs. Use a small local model (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`, ~80MB) to keep inference local. Return the reranked top-k.
- **Expected outputs:** `retrieval/rerank.py` with `CrossEncoderReranker` class. Reranking eval comparison.
- **Dependencies:** `sentence-transformers` (already an optional dependency).
- **Tests:** `tests/test_rerank.py` — reranking changes ordering of known passages.
- **Acceptance criteria:** Reranking experiment shows measurable recall or precision change. If latency increase > 5s per query with no quality gain, document and defer.
- **Definition of done:** Reranker available as optional retrieval stage. Experiment results documented.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 2.7: Alternative Fusion Strategies
- **Technical approach:** Extend `retrieval/fusion.py` with: (a) weighted RRF (different k per retriever), (b) CombSUM (sum of normalized scores), (c) CombMNZ (CombSUM × number of retrievers that returned the document). Compare all strategies on the domain eval set.
- **Expected outputs:** Extended fusion module. Comparison table of fusion strategies.
- **Dependencies:** Task 2.2 (entity linking improvements should be in place).
- **Tests:** `tests/test_fusion.py` extended with new strategies.
- **Acceptance criteria:** At least one non-RRF strategy evaluated. Best strategy identified for the domain corpus.
- **Definition of done:** Fusion comparison documented. Default strategy chosen based on evidence.
- **Priority:** P2 | **Complexity:** Low | **Effort:** 1 day

---

### Phase 3 — Adaptive Agent

**Objective:** Transform the bounded planner into an adaptive retrieval agent.

#### Task 3.1: Query Intent Classification
- **Technical approach:** Classify incoming questions into categories: single-hop, multi-hop, comparison, broad research. Two approaches to evaluate:
  1. **Heuristic:** Keyword patterns ("compare", "which ... better", "what are the differences" → comparison; "how does X relate to Y through Z" → multi-hop).
  2. **LLM-based:** Use Qwen3 4B with structured output to classify.
  Compare accuracy of both on a labeled subset of domain questions (the existing questions have `hop_count` metadata that can serve as partial ground truth).
- **Expected outputs:** `agent/query_classifier.py` with `classify_query()`. Classification accuracy on labeled subset.
- **Dependencies:** None (can start in parallel with Phase 2).
- **Tests:** `tests/test_query_classifier.py` — known questions map to expected categories.
- **Acceptance criteria:** Classification accuracy ≥ 0.75 on 1-hop vs multi-hop distinction (using existing `hop_count` labels). If heuristic matches LLM accuracy, prefer heuristic (lower latency).
- **Definition of done:** Classifier integrated into agent. Classification logged in agent output.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 3.2: Query Decomposition for Multi-Hop Questions
- **Technical approach:** For questions classified as multi-hop, use Qwen3 4B to decompose into sub-questions before the planner loop begins. Add a `decompose` action to the planner schema. Compare: (a) reactive decomposition (current: planner generates sub-queries one at a time), (b) upfront decomposition (generate all sub-questions first, then retrieve for each).
- **Expected outputs:** `agent/query_decomposer.py`. Comparison of reactive vs upfront decomposition on multi-hop domain questions.
- **Dependencies:** Task 3.1 (query classifier).
- **Tests:** `tests/test_query_decomposer.py` — known multi-hop questions produce reasonable sub-questions.
- **Acceptance criteria:** Decomposition produces ≥2 sub-questions for 2+ hop questions. Agent eval F1 on multi-hop questions does not decrease.
- **Definition of done:** Decomposition available as configurable agent option.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 3.3: Adaptive Tool Routing
- **Technical approach:** Use query classification to bias tool selection:
  - Single-hop → prefer keyword or dense (fastest path).
  - Multi-hop → prefer graph tool first, then keyword/dense for gap-filling.
  - Comparison → graph tool for entity pairs, then dense for evidence.
  - Broad research → keyword first for coverage, then dense for diversity.
  Implement as routing hints in the planner system prompt rather than hard-coded rules, preserving the planner's ability to override.
- **Expected outputs:** Modified planner prompt with routing hints. Comparison of adaptive vs fixed routing.
- **Dependencies:** Tasks 3.1, 3.2, Phase 2 (graph retrieval should be improved first).
- **Tests:** Agent eval with routing logging; measure tool selection distribution by query type.
- **Acceptance criteria:** Adaptive routing matches or exceeds fixed routing on overall F1. Tool selection distribution shifts measurably by query type.
- **Definition of done:** Routing strategy documented. Experiment results show whether adaptive routing helps.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 3.4: Evidence Sufficiency Detection
- **Technical approach:** Add a heuristic sufficiency check after each retrieval step:
  1. Count of unique passages retrieved.
  2. Coverage of sub-questions (if decomposed).
  3. Similarity between retrieved passages and the question (using cached embeddings).
  Surface sufficiency signal to the planner as additional context. The planner retains final stop decision.
- **Expected outputs:** `agent/sufficiency.py` with `is_sufficient()`. Reduced unnecessary tool calls.
- **Dependencies:** Tasks 3.1, 3.2.
- **Tests:** `tests/test_sufficiency.py` — known sufficient/insufficient evidence sets.
- **Acceptance criteria:** Average tool calls per question decreases by ≥0.5 without F1 decrease.
- **Definition of done:** Sufficiency check integrated into agent loop. Tool call statistics documented.
- **Priority:** P2 | **Complexity:** Medium | **Effort:** 2 days

---

### Phase 4 — Evaluation and Research Validation

**Objective:** Run comprehensive evaluations and produce publishable results.

#### Task 4.1: Comprehensive Retrieval Ablation Suite
- **Technical approach:** Create `eval/run_ablation_suite.py` that runs all retrieval combinations systematically:
  1. BM25 only
  2. Dense only
  3. Graph only (original)
  4. Graph only (improved entity linking)
  5. BM25 + Dense RRF
  6. BM25 + Graph RRF
  7. Dense + Graph RRF
  8. BM25 + Dense + Graph RRF
  9. Graph with hop depth 1, 2, 3
  10. Graph with improved entity linking + reranking
  11. All of the above with cross-encoder reranking
  Save all results as machine-readable JSON with config snapshots and input checksums.
- **Expected outputs:** Complete ablation table with bootstrap CIs and paired comparisons for all variants.
- **Dependencies:** Phases 1, 2 (graph and retrieval improvements).
- **Tests:** All result files are valid JSON with required fields.
- **Acceptance criteria:** ≥10 ablation variants compared on the same frozen question set. Paired bootstrap 95% CIs computed for all pairwise comparisons vs BM25 baseline.
- **Definition of done:** Ablation results committed to `eval/results/`. Summary table in `eval/results-summary.md`.
- **Priority:** P0 | **Complexity:** Medium | **Effort:** 2 days

#### Task 4.2: Faithfulness Evaluation
- **Technical approach:** Create `eval/faithfulness_judge.py` using Qwen3 8B as an LLM judge. For each (question, answer, retrieved_passages) triple, the judge outputs: FAITHFUL / NOT_FAITHFUL / PARTIALLY_FAITHFUL with explanation. Calibrate against 50 human-labeled examples. Report agreement rate and Cohen's kappa.
- **Expected outputs:** Faithfulness scores for all answer evaluation runs. Calibration report.
- **Dependencies:** Human-labeled faithfulness subset (30-50 examples).
- **Tests:** `tests/test_faithfulness.py` — judge produces valid output for known faithful/unfaithful examples.
- **Acceptance criteria:** Judge-human agreement ≥ 0.70 Cohen's kappa on calibration set.
- **Definition of done:** Faithfulness metric added to `eval/answer_metrics.py`. Results include faithfulness scores.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 3 days

#### Task 4.3: Extended Agent Evaluation
- **Technical approach:** Run `eval/run_agent_eval.py --per-hop 10` for a 30-question agent evaluation (10 per hop bucket). Compare against BM25-only answers on the same questions. Measure: EM, F1, citation validity, supporting recall, tool calls, latency.
- **Expected outputs:** Agent evaluation results with bootstrap CIs. Head-to-head comparison vs BM25.
- **Dependencies:** Phase 3 (adaptive agent improvements).
- **Tests:** Agent eval completes for all 30 questions.
- **Acceptance criteria:** Agent results documented with honest comparison. If agent underperforms BM25, the gap and its causes are documented.
- **Definition of done:** Agent evaluation committed to `eval/results/`. Comparison table in `eval/results-summary.md`.
- **Priority:** P0 | **Complexity:** Low (operational) | **Effort:** 2 days (wall-clock; ~77s/question × 30 ≈ 40 min compute)

#### Task 4.4: Additional Benchmark Investigation
- **Technical approach:** Evaluate suitability of HotpotQA and 2WikiMultiHopQA:
  - **HotpotQA:** Well-established multi-hop QA benchmark. 2-hop questions only. Large corpus (5M+ Wikipedia paragraphs). Limitation: not domain-specific, so graph ontology may not apply.
  - **2WikiMultiHopQA:** Multi-hop with more structured reasoning chains. Limitation: synthetic construction may not reflect real research questions.
  Recommendation: Use MuSiQue (already frozen at 300 questions) as the primary public benchmark. Consider HotpotQA only if a second public benchmark is needed for credibility. Do not add 2WikiMultiHop unless there is a specific question type it covers that MuSiQue does not.
- **Expected outputs:** Written assessment of benchmark suitability. Decision on whether to add a second benchmark.
- **Dependencies:** None.
- **Acceptance criteria:** Decision documented with reasoning.
- **Definition of done:** Assessment in this roadmap or in `eval/README.md`.
- **Priority:** P2 | **Complexity:** Low | **Effort:** 0.5 days

#### Task 4.5: Error Categorization Study
- **Technical approach:** Sample 40 incorrect answers (≥10 per hop bucket) from the best-performing retrieval variant. For each, manually categorize the error cause:
  - **Extraction miss:** Relevant triple not extracted from passage.
  - **Entity resolution error:** Correct entity exists but not linked.
  - **Retrieval failure:** Correct passage not retrieved.
  - **Decomposition error:** Wrong sub-question generated.
  - **Expansion noise:** Correct passage diluted by irrelevant expansions.
  - **Generation error:** Correct evidence retrieved but wrong answer generated.
- **Expected outputs:** Error distribution chart. Actionable insights for further improvement.
- **Dependencies:** Phase 2 + Phase 4 answer eval.
- **Tests:** Error categorization covers ≥40 examples.
- **Acceptance criteria:** ≥80% of errors assigned a category. Dominant error category identified.
- **Definition of done:** Error analysis in `docs/error_analysis.md`. Referenced from README.
- **Priority:** P1 | **Complexity:** Medium (human effort) | **Effort:** 2 days

---

### Phase 5 — Visual Evidence Explorer

**Objective:** Make retrieval and reasoning transparent through a research-oriented UI.

#### Task 5.1: Evidence Explorer Panel
- **Technical approach:** Extend the existing `ui/index.html` to show retrieved passages below the answer. For each passage, display: passage ID, paper title, passage text (truncated to 200 chars with expand), retrieval source (keyword/vector/graph), retrieval score. Link citation IDs to their passage entries.
- **Expected outputs:** Enhanced UI with passage inspection. CSS-only accordion for passage expansion.
- **Dependencies:** Task 0.3 (API/UI verified working).
- **Tests:** Manual browser test — passages display, expand, and link to citations.
- **Acceptance criteria:** All cited passages are visible and inspectable. Users can see why each passage was selected.
- **Definition of done:** UI shows passages for all answers.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 2 days

#### Task 5.2: Agent Execution Timeline
- **Technical approach:** Extend the existing step display (`ui/index.html` L132-145) into a visual timeline. Show: step number, tool selected, query generated, result count, latency. Use CSS grid or flexbox for horizontal timeline layout. No external dependencies.
- **Expected outputs:** Visual timeline of agent execution steps.
- **Dependencies:** Task 5.1.
- **Tests:** Manual browser test — timeline renders for multi-step agent queries.
- **Acceptance criteria:** Each agent step is individually inspectable. Timeline shows query, tool, and result count.
- **Definition of done:** Timeline visible for all agent queries.
- **Priority:** P2 | **Complexity:** Low | **Effort:** 1 day

#### Task 5.3: Interactive Knowledge Graph Visualization
- **Technical approach:** Add a lightweight graph visualization using D3.js force-directed layout or Cytoscape.js (both MIT-licensed, self-hosted). Show: entities as labeled nodes (colored by type), relationships as labeled edges, highlight the subgraph traversed during graph retrieval. Add a new API endpoint `GET /graph/subgraph?entity_ids=...&hops=2` that returns the local neighborhood.
- **Expected outputs:** Interactive graph panel showing relevant entities and traversal paths. New API endpoint.
- **Dependencies:** Tasks 5.1, 5.2. Phase 1 (audited graph).
- **Tests:** Manual browser test — graph renders, nodes are interactive, paths are highlighted.
- **Acceptance criteria:** Graph visualization renders ≤100 nodes without performance issues. Traversed paths are visually distinct.
- **Definition of done:** Graph panel integrated into main UI or accessible as a separate view.
- **Priority:** P2 | **Complexity:** High | **Effort:** 3 days

#### Task 5.4: Retrieval Comparison Dashboard
- **Technical approach:** Create a static dashboard that reads eval result JSON files and renders comparison tables and bar charts. Use vanilla JS with HTML `<canvas>` or a single lightweight chart library (Chart.js, ~60KB). Show: recall by variant, recall by hop count, latency comparison, confidence intervals as error bars.
- **Expected outputs:** Dashboard rendering eval results as charts.
- **Dependencies:** Phase 4 (ablation results).
- **Tests:** Manual browser test — charts render from existing result files.
- **Acceptance criteria:** Dashboard displays ≥4 retrieval variants with recall and latency comparisons.
- **Definition of done:** Dashboard accessible from the UI or as a standalone page.
- **Priority:** P2 | **Complexity:** Medium | **Effort:** 2 days

---

### Phase 6 — Packaging and Documentation

**Objective:** Make the project easy for another developer or researcher to run.

#### Task 6.1: Dockerfile
- **Technical approach:** Multi-stage Dockerfile:
  - Stage 1: Python 3.11-slim, install package with all optional dependencies.
  - Stage 2: Copy application code and data.
  - Entrypoint: `uvicorn api.app:app --host 0.0.0.0 --port 8000`.
  Do NOT bundle Ollama inside the same container (separate concern; Ollama has its own Docker image).
- **Expected outputs:** `Dockerfile` that builds and runs the API.
- **Dependencies:** Phase 0 (verified working system).
- **Tests:** `docker build -t agentic-graphrag .` succeeds. Container starts and responds to `/healthz`.
- **Acceptance criteria:** Container starts in <60s. `/healthz` returns valid JSON. `/ask` works when Ollama is accessible.
- **Definition of done:** Dockerfile committed. Build instructions in README.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 1 day

#### Task 6.2: Docker Compose with Ollama
- **Technical approach:** `docker-compose.yml` with two services:
  - `ollama`: Official Ollama Docker image with volume for model storage.
  - `app`: Built from Dockerfile, depends on Ollama, environment variables from `.env`.
  Add a startup script that pulls required models if not present.
- **Expected outputs:** `docker-compose.yml`. `docker compose up` starts the full system.
- **Dependencies:** Task 6.1.
- **Tests:** `docker compose up -d` starts both services. API responds after model pull.
- **Acceptance criteria:** `docker compose up` starts the system. Models are automatically pulled on first run.
- **Definition of done:** Docker Compose file committed. Instructions in README.
- **Priority:** P1 | **Complexity:** Medium | **Effort:** 1 day

#### Task 6.3: CI Expansion
- **Technical approach:** Add `.github/workflows/test.yml`:
  - Run `pytest tests/` on every push/PR.
  - Run `ruff check .` for linting.
  - Keep existing `retrieval-eval.yml` for BM25 recall gate.
  Future: Add answer evaluation gate (requires Ollama in CI — deferred until Docker is ready).
- **Expected outputs:** CI workflow for unit tests and linting.
- **Dependencies:** Task 0.2 (unit tests exist).
- **Tests:** CI passes on clean checkout.
- **Acceptance criteria:** All PRs run unit tests and linting. Failures block merge.
- **Definition of done:** Workflow file committed. CI badge in README.
- **Priority:** P1 | **Complexity:** Low | **Effort:** 0.5 days

#### Task 6.4: Complete Documentation
- **Technical approach:** Update `README.md` with:
  - Architecture diagram (existing Mermaid, extend with graph pipeline).
  - Quick start instructions (from `QUICKSTART.md`).
  - Benchmark results table (from `eval/results-summary.md`).
  - Failure gallery (5-10 illustrative errors with explanations).
  - Cost and latency analysis.
  - Limitations section (updated).
  - Links to all sub-READMEs.
  Create `docs/architecture.md` with detailed component diagrams.
- **Expected outputs:** Comprehensive README. Architecture documentation.
- **Dependencies:** All phases.
- **Tests:** All links work. All referenced files exist.
- **Acceptance criteria:** A new developer can understand the project from the README alone.
- **Definition of done:** README reviewed and merged.
- **Priority:** P1 | **Complexity:** Low | **Effort:** 1 day

#### Task 6.5: Demonstration Video Script
- **Technical approach:** Write `docs/demo-script.md` with a 2-minute demo script:
  1. Show the question input.
  2. Show agent thinking (tool selection, sub-queries).
  3. Show answer with citations.
  4. Show evidence explorer (passages, graph visualization).
  5. Show evaluation dashboard.
  Record using screen capture tool.
- **Expected outputs:** Demo script. Recorded video.
- **Dependencies:** All phases (system must be complete).
- **Tests:** Video plays and covers all script points.
- **Acceptance criteria:** Video is ≤3 minutes. All key features are demonstrated.
- **Definition of done:** Video uploaded and linked from README.
- **Priority:** P2 | **Complexity:** Low | **Effort:** 1 day


---

## Section 6: Experimental Research Design

### Experiment 1: Why Does Graph Retrieval Underperform?

**Research question:** What is the primary cause of graph-only recall@5 = 0.041 on the domain evaluation set?

**Hypothesis:** The dominant failure mode is entity linking — the BM25-over-names seeding fails to find relevant graph entities for most queries, so BFS never reaches useful passages.

**Dataset:** 98 answerable domain questions with known supporting passage IDs.

**Method:**
1. For each question, run `seed_entities()` and record the top-10 seeds.
2. Check whether any seed entity is connected (within 2 hops) to a node whose `source_chunk_ids` include a gold supporting passage.
3. Categorize each question as: (a) entity found + passage reached, (b) entity found + passage not reached, (c) entity not found + entity exists in graph, (d) entity not in graph.
4. Compute the distribution across categories.

**Baselines:** Current BM25 entity seeding vs. oracle entity seeding (manually provide correct entity IDs).

**Metrics:** Seed entity precision@10, gold passage reachability rate, recall@5 under oracle seeding.

**Statistical validation:** Bootstrap 95% CIs on reachability rates.

**Expected outcome:** If oracle seeding dramatically improves recall (e.g., from 0.041 to 0.3+), entity linking is the bottleneck. If oracle seeding shows only modest improvement, graph coverage or traversal is the bottleneck.

---

### Experiment 2: Does Better Entity Linking Improve Graph Recall?

**Research question:** How much does improved entity linking contribute to graph retrieval quality?

**Hypothesis:** Hybrid entity linking (fuzzy matching + alias expansion + embeddings) will improve seed entity precision and downstream recall.

**Dataset:** Same 98 domain questions.

**Method:**
1. Implement improved entity linker (Task 2.2).
2. Run graph retrieval with original BM25 seeding vs. improved seeding.
3. Compare recall@5, seed precision@10, and gold passage reachability.

**Controlled variable:** Entity linking method. All other parameters (hops=2, max_nodes=100, max_chunks=30, decay=0.5) held constant.

**Metrics:** Recall@5, seed entity precision@10, seed entity recall@10 (requires annotation of correct entities per question).

**Statistical validation:** Paired bootstrap 95% CI on recall difference.

**Ablation:** Also test each linking component in isolation: (a) fuzzy matching only, (b) alias expansion only, (c) dense embedding only, (d) all combined.

---

### Experiment 3: Does Relation-Aware Traversal Improve Multi-Hop Retrieval?

**Research question:** Does filtering or weighting BFS edges by predicate type improve retrieval for multi-hop questions?

**Hypothesis:** For questions about evaluation results (e.g., "What dataset did X use?"), prioritizing EVALUATES_ON and USES edges will retrieve more relevant passages than uniform BFS.

**Dataset:** Same 98 domain questions, stratified by hop count.

**Method:**
1. Run graph retrieval with uniform edge weights (current).
2. Run with predicate-weighted edges (e.g., EVALUATES_ON: 1.5×, USES: 1.2×, CITES: 0.5×).
3. Run with predicate filtering (only follow edges matching the question intent).
4. Compare recall@5 across all three settings, stratified by hop count.

**Controlled variables:** Entity linking method (use improved linker from Experiment 2). Score decay, hop depth, node/chunk limits held constant.

**Metrics:** Recall@5 overall and by hop count. Paired bootstrap CIs.

**Expected outcome:** Relation-aware traversal may help for specific question types but could hurt for others. Stratify results by question type if possible.

---

### Experiment 4: What Is the Optimal Graph Hop Depth?

**Research question:** What BFS hop depth maximizes graph retrieval quality on the domain corpus?

**Hypothesis:** Hop depth 2 is optimal for 2-hop questions, but 3-hop questions may benefit from depth 3.

**Dataset:** Same 98 domain questions.

**Method:** Run graph retrieval at hop depths 1, 2, 3, and 4 on the full question set. Also run stratified by question hop count to check whether matching graph depth to question complexity helps.

**Controlled variables:** Entity linking (improved), score decay (best from Experiment 4), all other parameters fixed.

**Metrics:** Recall@5 by hop depth × question hop count. Node expansion count (measure noise).

**Statistical validation:** Paired bootstrap CIs for each depth vs depth=2 (current default).

**Note:** This experiment partially exists (domain_graph_hops1_k5_v0.1.json and domain_graph_hops2_k10_v0.1.json) but was run on the unaudited graph. Re-run after Phase 1 audit.

---

### Experiment 5: Does Graph + Dense Retrieval Beat Dense Retrieval Alone?

**Research question:** On the domain evaluation set, does adding graph retrieval to dense retrieval via RRF improve recall?

**Hypothesis:** Graph retrieval will improve recall specifically on multi-hop questions where dense retrieval misses bridging passages.

**Dataset:** Same 98 domain questions.

**Method:**
1. Dense only (baseline).
2. Graph only (improved).
3. Dense + Graph RRF.
4. BM25 + Dense RRF.
5. BM25 + Dense + Graph RRF.
Compare all five, stratified by hop count.

**Controlled variables:** All entity linking improvements applied. Same RRF k=60.

**Metrics:** Recall@5 overall and by hop count. Paired bootstrap CIs for all comparisons vs BM25 baseline.

**Key comparison:** Does #5 (triple fusion) outperform #4 (BM25+Dense) on multi-hop questions? The current result (#5 scores 0.349 vs #4 at 0.327) is on the unaudited graph. Re-evaluate after audit and entity linking improvements.

---

### Experiment 6: Does Adaptive Routing Beat Fixed Hybrid Retrieval?

**Research question:** Does query-dependent tool selection improve over fixed hybrid retrieval?

**Hypothesis:** Single-hop questions are better served by BM25/dense alone, while multi-hop questions benefit from graph retrieval. Adaptive routing should match or exceed any single fixed strategy.

**Dataset:** Same 98 domain questions, plus the 300 public MuSiQue questions.

**Method:**
1. Fixed BM25 (baseline).
2. Fixed BM25 + Dense RRF.
3. Fixed BM25 + Dense + Graph RRF.
4. Adaptive agent with routing (Phase 3).
Compare on both domain and public tracks.

**Controlled variables:** Answer model (Qwen3 8B), temperature (0.0), max steps (5).

**Metrics:** Token F1, EM, citation validity, tool calls per question, latency. Paired bootstrap CIs.

**Key question:** Does the adaptive agent provide enough quality improvement to justify 5× latency increase (77.4s vs 14.4s)?

---

### Experiment 7: Does Reranking Improve Evidence Quality?

**Research question:** Does cross-encoder reranking improve the quality of the final passage set?

**Hypothesis:** Reranking will improve precision of the top-k set, leading to better answer generation even if recall@k is unchanged.

**Dataset:** Same 98 domain questions.

**Method:**
1. BM25 + Dense RRF (top 5, no reranking).
2. BM25 + Dense RRF (top 50 candidates, rerank to top 5).
3. BM25 + Dense + Graph RRF (top 50 candidates, rerank to top 5).
For each, generate answers and compare token F1 and faithfulness.

**Controlled variables:** Same answer model, temperature, and retrieved candidate pool size.

**Metrics:** Recall@5, token F1, faithfulness (if calibrated), latency. Paired bootstrap CIs.

**Latency consideration:** Cross-encoder adds ~1-3s per query for 50 passages on CPU. Acceptable if quality improvement is measurable.

---

### Experiment 8: Does Improved Retrieval Translate into Better Final Answers?

**Research question:** Do improvements in retrieval recall translate into improvements in answer quality?

**Hypothesis:** Higher retrieval recall does not guarantee better answers. The answer model must also be able to synthesize information from the retrieved passages.

**Dataset:** 30-question stratified domain sample (existing `questions_answer_eval_stratified_v0.1.jsonl`).

**Method:**
1. Generate answers using BM25 top-5 passages (existing baseline: F1 0.287).
2. Generate answers using the best-performing retrieval variant from Experiments 1-7.
3. Generate answers using oracle retrieval (gold supporting passages provided directly).
Compare F1, EM, and faithfulness across all three.

**Key insight:** The gap between #2 and #3 measures the remaining retrieval bottleneck. The gap between #3 and perfect F1 measures the generation bottleneck.

**Metrics:** Token F1, EM, faithfulness, latency. Paired bootstrap CIs.

---

## Section 7: Technical Decisions

### Decision 1: In-Memory Graph vs. Neo4j

| Factor | In-Memory Graph | Neo4j |
|---|---|---|
| **Current state** | Fully implemented (`retrieval/graph.py`) | Loader exists (`graph/load_neo4j.py`), dry-run only |
| **Query latency** | Sub-millisecond (data in RAM) | 1-10ms (network + disk) |
| **Setup complexity** | Zero (loads from JSONL) | Requires running Neo4j server |
| **Graph size limit** | ~10K nodes / ~5K edges fits easily in RAM | Scales to millions |
| **Cypher query flexibility** | None (Python BFS only) | Full Cypher support |
| **Visualization** | Must build custom | Neo4j Browser built-in |

**Recommendation:** **Keep in-memory graph as the primary retrieval backend.** The current graph (994 nodes, 581 edges) and projected full graph (~5K nodes, ~3K edges) fit comfortably in memory. Neo4j adds operational complexity without a clear benefit at this scale.

**When to reconsider:** If the graph exceeds 50K nodes, or if Cypher queries become necessary for complex traversal patterns that BFS cannot express efficiently.

**Action:** Keep the Neo4j loader available as an optional export for visualization and exploration, but do not integrate it into the retrieval path.

---

### Decision 2: BFS vs. Relation-Aware Traversal

| Factor | Uniform BFS (current) | Relation-Aware BFS | Learned Traversal |
|---|---|---|---|
| **Complexity** | Low | Medium | High |
| **Explainability** | High (deterministic) | High (rules are explicit) | Low |
| **Tuning effort** | Minimal | Moderate (predicate weights) | High (training data needed) |
| **Expected benefit** | Baseline | Moderate (hypothesis) | Unknown |

**Recommendation:** **Implement relation-aware BFS as a configurable extension, not a replacement.** Add predicate weights to `expand()` as an optional parameter with default=1.0 for all predicates. Run Experiment 3 to determine whether weighting helps. Do not pursue learned traversal unless Experiment 3 shows strong signal.

---

### Decision 3: RRF vs. Alternative Fusion Strategies

| Factor | RRF (k=60) | Weighted RRF | CombSUM | CombMNZ |
|---|---|---|---|---|
| **Current state** | Implemented | Not implemented | Not implemented | Not implemented |
| **Parameter sensitivity** | Low (robust to k choice) | Moderate (weight tuning) | High (score normalization) | Moderate |
| **Theoretical basis** | Well-studied | Extension of RRF | Classic IR | Classic IR |
| **Implementation effort** | Done | 10 lines | 15 lines | 15 lines |

**Recommendation:** **Keep RRF as the default.** Implement alternatives for experimentation but do not switch without experimental evidence (Task 2.7). RRF's robustness and simplicity are strengths.

---

### Decision 4: Local Cross-Encoder vs. Simpler Reranking

| Factor | Cross-Encoder | BM25 Reranking | Score Interpolation |
|---|---|---|---|
| **Quality** | Highest (learned relevance) | Moderate | Low |
| **Latency** | 1-3s for 50 passages (CPU) | <10ms | <1ms |
| **Dependencies** | sentence-transformers model (~80MB) | None | None |
| **Local-first** | Yes (runs locally) | Yes | Yes |

**Recommendation:** **Implement cross-encoder reranking as an optional stage.** Use `cross-encoder/ms-marco-MiniLM-L-6-v2` (Apache 2.0 license, ~80MB, runs on CPU). Add to `retrieval/rerank.py` with a config flag to enable/disable. Run Experiment 7 to determine whether the quality improvement justifies the latency cost.

---

### Decision 5: Vanilla JS vs. Frontend Framework

| Factor | Vanilla JS (current) | React/Vue/Svelte |
|---|---|---|
| **Current state** | 153 lines, working scaffold | Not started |
| **Dependencies** | Zero | npm, bundler, framework |
| **Build step** | None | Required |
| **Complexity ceiling** | ~500 lines before becoming unwieldy | Unlimited |
| **Graph visualization** | D3.js works with vanilla JS | Wrapper libraries available |
| **Learning curve** | None | Framework-specific |

**Recommendation:** **Stay with vanilla JS for the core UI. Add D3.js or Cytoscape.js only for graph visualization.** The UI requirements (answer display, passage inspection, agent timeline, graph visualization) can be met with ~400-500 lines of vanilla JS + one visualization library. A frontend framework would add build complexity without proportional benefit for this research tool.

**When to reconsider:** If the UI grows beyond ~800 lines or requires complex state management (e.g., multi-panel synchronized views).

---

### Decision 6: Custom Evaluation vs. External Frameworks (RAGAS, etc.)

| Factor | Custom Eval (current) | RAGAS | DeepEval |
|---|---|---|---|
| **Current state** | Complete suite with EM, F1, citation, recall, bootstrap CIs | Not installed | Not installed |
| **Control** | Full | Framework-defined metrics | Framework-defined metrics |
| **Metric alignment** | Exact match to project needs | Generic RAG metrics | Generic RAG metrics |
| **Reproducibility** | Deterministic (seeded bootstrap) | Depends on LLM judge | Depends on LLM judge |
| **Dependencies** | stdlib only (except sentence-transformers for dense) | openai, langchain, etc. | openai, etc. |

**Recommendation:** **Keep the custom evaluation suite as the primary framework.** The existing eval code is well-designed, deterministic, and aligned with the project's specific metrics. Consider RAGAS only for its faithfulness metric implementation — but implement a custom faithfulness judge instead (Task 4.2) to maintain local-first design and avoid hosted API dependencies.

**Rationale:** RAGAS and DeepEval typically require hosted LLM APIs for evaluation, which conflicts with the local-first design. The custom eval suite already provides: recall@k, EM, token F1, citation metrics, bootstrap CIs, paired comparisons, and hop-stratified reporting.

---

## Section 8: Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Incorrect graph relationships** — extraction LLM hallucinates triples | High (46.7% rejection rate already observed) | High — corrupts graph retrieval | Phase 1 audit establishes accuracy baseline. Improve extraction prompt (Task 1.4). Use confidence thresholds to filter low-quality triples. |
| 2 | **Poor entity resolution** — duplicate entities remain after resolution | Medium | High — inflates graph, reduces link density | Embedding-based candidate generation (implemented). Human adjudication (Task 1.2). LLM-assisted disambiguation for scale (Task 1.3). |
| 3 | **Retrieval latency** — agent takes 77.4s vs 14.4s for BM25 | Confirmed | Medium — limits usability | Adaptive routing (Task 3.3) to use simpler tools for simple questions. Cache embeddings (already implemented). Evidence sufficiency to stop early (Task 3.4). |
| 4 | **Local hardware limitations** — Qwen3 8B requires ~8GB VRAM; embedding on CPU is slow | Medium | Medium — limits who can run the system | Document minimum hardware requirements. Support CPU-only mode (already works). Provide pre-computed embedding caches. |
| 5 | **LLM extraction errors** — Qwen3 4B is a small model for extraction | High | Medium — extraction quality ceiling | Monitor rejection rate. Consider larger extraction model if quality audit shows <70% accuracy. Prompt engineering (Task 1.4) may recover quality without model change. |
| 6 | **Benchmark leakage** — eval questions derived from corpus could overlap with training data | Low (domain questions are hand-written) | High — invalidates results | MuSiQue is a published benchmark (leakage is a community-wide concern, not project-specific). Domain questions are project-specific and not in training data. Document this consideration. |
| 7 | **Unreliable citations** — model cites passages that don't support the answer | Confirmed (citation validity 0.933 on domain) | Medium — misleads users | Citation validation (implemented) forces abstention on invalid citations. Faithfulness judge (Task 4.2) will measure this systematically. |
| 8 | **Prompt injection** — adversarial content in retrieved passages | Low (corpus is research papers) | High — security vulnerability | Prompt injection smoke test (implemented, 5/5 passed). Untrusted-evidence framing in all prompts. Passage text treated as data, not instructions. |
| 9 | **Corpus licensing** — research papers may have usage restrictions | Medium | High — could prevent public deployment | ArXiv papers are typically under CC-BY or similar licenses. Document license for each paper. Do not serve full paper text through the API — only extracted entities and short passages. Consult institutional guidance before public deployment. |
| 10 | **Dependency complexity** — adding too many libraries increases maintenance burden | Medium | Low | Keep core dependencies minimal (currently zero required deps). Add libraries only with documented justification. Prefer stdlib alternatives where possible. |
| 11 | **Inconsistent experiment results** — LLM nondeterminism affects reproducibility | Medium (temperature=0.0 mitigates) | Medium | Use temperature=0.0 (already configured). Seed all random operations (already done). Save model version and config hash with every result. |
| 12 | **Graph retrieval may never outperform BM25** — fundamental limitation | Medium | High — undermines project thesis | This is a valid research finding. Document where graph helps and where it doesn't. Focus on multi-hop questions where graph has theoretical advantage. Frame negative results as scientific contribution. |

---

## Section 9: Final Deliverables

The completed project should contain:

### 9.1 Audited Knowledge Graph
- [ ] Full-corpus graph (all 325 papers, ~10,878 passages).
- [ ] Triple accuracy measured with Wilson 95% CI on ≥50 random edges.
- [ ] Entity resolution completed on all candidate pairs.
- [ ] Entity resolution precision documented.
- [ ] Alias collisions resolved to 0.
- [ ] Graph quality report with all metrics.

### 9.2 Improved Graph Retrieval
- [ ] Improved entity linking with measurable precision.
- [ ] Tuned score decay and hop depth.
- [ ] Relation-aware traversal evaluated.
- [ ] Cross-encoder reranking available.
- [ ] Graph retrieval contribution measured on multi-hop questions.

### 9.3 Adaptive Query Routing
- [ ] Query intent classifier.
- [ ] Query decomposition for multi-hop questions.
- [ ] Adaptive tool routing with logged decisions.
- [ ] Evidence sufficiency detection.
- [ ] Bounded execution preserved (max 5 steps).

### 9.4 Comprehensive Evaluation Suite
- [ ] MuSiQue 300-question public benchmark (existing).
- [ ] 109-question domain benchmark (existing).
- [ ] ≥10 retrieval ablation variants compared.
- [ ] Faithfulness evaluation with calibrated LLM judge.
- [ ] Agent evaluation on ≥30 questions.
- [ ] Error categorization study (≥40 examples).
- [ ] All results with bootstrap 95% CIs and paired comparisons.
- [ ] Machine-readable result files with config snapshots.

### 9.5 Research-Oriented Visual Explorer
- [ ] Evidence explorer showing retrieved passages.
- [ ] Agent execution timeline.
- [ ] Interactive knowledge graph visualization.
- [ ] Retrieval comparison dashboard.

### 9.6 Dockerized Setup
- [ ] Dockerfile for application.
- [ ] Docker Compose with Ollama.
- [ ] Documented environment variables.
- [ ] Startup script with model pulling.

### 9.7 Automated Tests and CI
- [ ] Unit tests for core modules (≥80% coverage).
- [ ] CI workflow for tests and linting.
- [ ] BM25 recall quality gate (existing).
- [ ] Reproducible benchmark results.

### 9.8 Complete Technical Documentation
- [ ] Updated README with architecture, results, and instructions.
- [ ] Architecture diagrams.
- [ ] Quick start guide.
- [ ] Benchmark report.
- [ ] Error analysis document.
- [ ] Graph retrieval diagnosis.

### 9.9 Demonstration
- [ ] Demo video (≤3 minutes).
- [ ] Sample research queries with expected outputs.

---

## Section 10: Resume and Research Outcomes

### Measurable Achievements (to be filled with actual numbers after implementation)

The following outcomes can be reported once measured. **Do not claim these until the experiments are complete.**

| Achievement | Metric | How Measured | Current Baseline |
|---|---|---|---|
| Audited knowledge graph | Triple accuracy ± Wilson CI | `graph/audit_triples.py --score` | Not yet measured (worksheet pending) |
| Entity resolution | Resolution precision on adjudicated pairs | Manual review of merged entities | Not yet measured (307 candidates pending) |
| Graph entity count | Total nodes after resolution | `graph/merge_graph_extractions.py` summary | 994 (20-paper pilot) |
| Graph relationship count | Total edges after resolution | `graph/merge_graph_extractions.py` summary | 581 (20-paper pilot) |
| Multi-hop retrieval improvement | Recall@5 improvement on 2+ hop questions (graph+BM25 vs BM25-only) | `eval/run_graph_eval.py` with paired bootstrap CI | -0.114 (graph hurts BM25 on current unaudited graph) |
| Answer quality | Token F1 on domain stratified sample | `eval/run_answer_eval.py` | 0.287 (BM25 + Qwen3 8B) |
| Citation precision | Gold citation precision on domain | `eval/run_answer_eval.py` | 0.237 |
| Adaptive routing accuracy | Tool selection matches oracle on annotated subset | Manual annotation + comparison | Not yet measured |
| Reduction in retrieval calls | Average tool calls per question (adaptive vs fixed) | Agent eval comparison | ~3 calls (3-question pilot) |
| Latency | Mean end-to-end latency | Agent eval | 77.4s (agent), 14.4s (BM25) |
| Abstention accuracy | Correct abstention rate on unanswerable questions | `eval/run_answer_eval.py` | 63.6% (7/11) |
| Prompt injection resistance | Pass rate on synthetic attack cases | `eval/run_prompt_injection_eval.py` | 100% (5/5) |

### Resume Bullet Template

Once experiments are complete, the resume bullet should follow this pattern:

> "Built an agentic multi-hop GraphRAG system over 325 ML/NLP research papers with a [N]-node, [M]-edge knowledge graph (triple accuracy [X]% ± [Y]%). Designed a [Q]-question evaluation suite with CI regression gating; graph-assisted retrieval [improved/did not improve] multi-hop recall@5 from [A] to [B] (paired 95% CI [C]–[D]). Documented [positive/negative] retrieval results across [K] ablation variants. Local Ollama inference at $0 API cost."

**Important:** Fill in actual numbers only. Do not claim improvements that are not measured. Negative results (graph doesn't help) are equally valid research contributions.

### Research Paper Potential

The project has potential for a short workshop paper or technical report if:
1. The graph retrieval diagnosis (Experiment 1) produces actionable insights about *why* graph retrieval underperforms on academic paper corpora.
2. The entity linking improvements (Experiment 2) show a clear path from failure to partial success.
3. The ablation study (Experiments 3-7) isolates specific conditions where graph retrieval helps vs. hurts.
4. The adaptive routing study (Experiment 6) shows query-dependent strategy selection is superior to any fixed strategy.

Even purely negative results ("graph retrieval does not improve multi-hop QA on small academic corpora under local LLM constraints") are publishable if rigorously measured and honestly reported.

---

## Appendix: Total Effort Estimate

| Phase | Estimated Days | Critical Path Dependencies |
|---|---|---|
| Phase 0: Repository Audit | 3–5 | None |
| Phase 1: KG Quality Audit | 5–8 | Phase 0 |
| Phase 2: Graph Retrieval | 8–12 | Phase 1 |
| Phase 3: Adaptive Agent | 6–8 | Phase 2 (partial) |
| Phase 4: Evaluation | 5–7 | Phases 2, 3 |
| Phase 5: Visual Explorer | 5–8 | Phase 1, Phase 0.3 |
| Phase 6: Packaging | 4–6 | All phases |
| **Total** | **36–54 engineering days** | |

> [!NOTE]
> Wall-clock time will be longer due to: (a) extraction compute (~48 hours for full corpus at 16s/passage), (b) human annotation time for triple audit and entity resolution, (c) Ollama inference time for evaluations (~77s/question for agent eval). Plan for 8–12 calendar weeks with part-time availability.

---

*End of Implementation Roadmap.*
