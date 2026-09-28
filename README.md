# Agentic GraphRAG

An experimental multi-hop retrieval system that combines dense retrieval, keyword search, and a knowledge graph. The project follows the staged plan in `docs/implementation-plan.md`: define the evaluation before building retrieval, then compare each system variant on the same questions.

## Current stage

Phase 0 setup is complete. Phase 1 data preparation is underway: a reproducible 300-question MuSiQue validation slice is committed, and 400 LLM-evaluation paper references are being reviewed for the domain corpus. The local smoke pipeline reads five fixture documents, normalizes metadata, splits text into configurable chunks, and writes a deterministic JSON artifact. Retrieval, embeddings, and Neo4j are not implemented yet.

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

No project benchmark results are reported yet. The public MuSiQue questions and candidate passage corpus are versioned in `eval/data/public/`. The domain paper references in `eval/data/domain/` still need full-text review, then questions and gold answers must be written and checked before retrieval features are implemented, as described in `docs/implementation-plan.md`.

