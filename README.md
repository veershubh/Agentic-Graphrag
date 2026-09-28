# Agentic GraphRAG

An experimental multi-hop retrieval system that combines dense retrieval, keyword search, and a knowledge graph. The project follows the staged plan in `docs/implementation-plan.md`: define the evaluation before building retrieval, then compare each system variant on the same questions.

## Current stage

Phase 0 setup is complete. Phase 1 data preparation is underway: a reproducible 300-question MuSiQue validation slice is committed, and the 400-reference domain bibliography has yielded 350 locally extractable full texts and 11,784 page-aware passages so far. The domain questions are a 56-question draft; hand review and expansion to the planned 100–150 questions are still in progress. The local smoke pipeline reads five fixture documents, normalizes metadata, splits text into configurable chunks, and writes a deterministic JSON artifact. Retrieval, embeddings, and Neo4j are not implemented yet.

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

No project benchmark results are reported yet. The public MuSiQue questions and candidate passage corpus are versioned in `eval/data/public/`. Domain references are versioned in `eval/data/domain/`; local PDF acquisition and extraction are still subject to full-text relevance and rights review. The current 56 domain questions are only a draft. The planned 100–150-question, hop-balanced domain evaluation must be completed and frozen before retrieval features are implemented, as described in `docs/implementation-plan.md`.

