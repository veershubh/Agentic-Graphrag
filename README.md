# Agentic GraphRAG

An experimental multi-hop retrieval system that combines dense retrieval, keyword search, and a knowledge graph. The project follows the staged plan in `docs/implementation-plan.md`: define the evaluation before building retrieval, then compare each system variant on the same questions.

## Current stage

Phase 0 setup is complete. The public 300-question MuSiQue slice and 109-question domain set are frozen. The provisional metadata inventory contains 325 papers and 10,878 page-aware passages, including the 57 frozen QA evidence-source papers; full-text relevance and rights review remains pending. Phase 2 has BM25, local dense, and BM25+dense RRF retrieval results on MuSiQue plus a citation-aware answer evaluator that has not been run. Phase 3 now has an evidence-linked ontology, a cacheable structured extraction pilot runner, graph consolidation, conservative alias review, Neo4j loading, and audit scaffolds. The paid extraction pilot has not been run, so there are no graph quality or cost results yet. Bounded graph retrieval, its domain evaluation command, and a single-query agent controller are implemented but unrun.

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

Retrieval-only public benchmark results are reported in `eval/README.md`; answer-generation metrics are not available because no API-backed answer run has been made. The public MuSiQue questions and candidate passage corpus are versioned in `eval/data/public/`; the domain evaluation set is frozen in `eval/data/domain/questions_v1.0.jsonl`. The 325-paper inventory remains provisional until full-text relevance and rights review is complete. Graph extraction, database loading, graph retrieval evaluation, agent runs, audits, API serving, and UI deployment remain unrun or incomplete; see `docs/implementation-plan.md` for phase-by-phase status.

