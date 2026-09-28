# Agentic GraphRAG

An experimental multi-hop retrieval system that combines dense retrieval, keyword search, and a knowledge graph. The project follows the staged plan in `docs/implementation-plan.md`: define the evaluation before building retrieval, then compare each system variant on the same questions.

## Current stage

Phase 0 setup is complete. Phase 1 data and evaluation preparation is underway: the 300-question MuSiQue slice and 109-question domain evaluation set are versioned. A metadata-only working inventory contains 325 extractable papers (including all 57 unique frozen QA evidence-source papers) and 10,878 page-aware passages. The inventory uses an abstract-screen threshold; manual full-text relevance and rights review is still pending. Phase 2 has BM25 and local dense baselines plus BM25+dense reciprocal-rank fusion on the public benchmark. An optional citation-constrained answer evaluator is implemented but has not been run; Neo4j graph retrieval remains future work.

## Quick start

Requires Python 3.11 or newer.

```powershell
python -m pip install -e .
python -m agentic_graphrag.pipeline --input data/smoke --output data/processed/smoke.json
```

Configuration lives in `configs/default.toml`. Run from the repository root. The smoke documents are synthetic fixtures for pipeline wiring, not evaluation data.

## Project layout

The folders follow the implementation plan: `ingest/`, `extract/`, `graph/`, `retrieval/`, `agent/`, `eval/`, `api/`, `ui/`, `configs/`, and `docs/`. Python code currently lives in `src/agentic_graphrag/` so it can be packaged and imported consistently.

## Evaluation status

Retrieval-only public benchmark results are reported in `eval/README.md`; answer generation and answer-quality results are not available yet. The public MuSiQue questions and candidate passage corpus are versioned in `eval/data/public/`; the domain evaluation set is frozen in `eval/data/domain/questions_v1.0.jsonl`. The 325-record domain paper inventory is provisional until full-text relevance and rights review is complete. Graph construction and agentic retrieval remain future work, as described in `docs/implementation-plan.md`.

