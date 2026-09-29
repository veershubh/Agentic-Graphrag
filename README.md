# Agentic GraphRAG

An experimental multi-hop retrieval system that combines dense retrieval, keyword search, and a knowledge graph. The project follows the staged plan in `docs/implementation-plan.md`: define the evaluation before building retrieval, then compare each system variant on the same questions.

## Current stage

Phase 0 setup is complete. The public 300-question MuSiQue slice and 109-question domain set are frozen. The provisional metadata inventory contains 325 papers and 10,878 page-aware passages, including the 57 frozen QA evidence-source papers; full-text relevance and rights review remains pending. Phase 2 has BM25, local dense, and BM25+dense RRF retrieval results on MuSiQue. In a stratified 30-question local answer sample, Qwen3 8B reached EM 0.10 and F1 0.216; answer quality remains weak. Phase 3's local Qwen3 pilot processed one passage from each of 20 papers: 175 entity records and 87 valid triples, with 58 invalid triples rejected. Phase 4's domain diagnostic found graph-only recall@5 of 0.071 and BM25+graph RRF recall@5 of 0.457, below BM25's 0.549. The graph is a small, unaudited sample and is not ready for production retrieval. Core LLM inference uses local Ollama and has no model API fees; local hardware, electricity, and one-time model downloads still have costs.

## Quick start

Requires Python 3.11 or newer.

```powershell
python -m pip install -e .
python -m agentic_graphrag.pipeline --input data/smoke --output data/processed/smoke.json
```

Configuration lives in `configs/default.toml`. Run from the repository root. The smoke documents are synthetic fixtures for pipeline wiring, not evaluation data.

## Local model setup

Install and start [Ollama](https://ollama.com/), then download the Apache 2.0 Qwen3 models once:

```powershell
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b
python graph/extract_domain_graph.py --max-passages-per-paper 1
```

Extraction and planning use Qwen3 4B; answer generation uses Qwen3 8B. Both run through the loopback Ollama server, which disables hidden thinking for schema-constrained requests so output tokens remain available for structured responses. The sentence-transformer embedding model also runs locally and downloads its weights on first use. No hosted LLM key is required. See `graph/README.md` for extraction results and `eval/README.md` for the answer-model comparison.

## Project layout

The folders follow the implementation plan: `ingest/`, `extract/`, `graph/`, `retrieval/`, `agent/`, `eval/`, `api/`, `ui/`, `configs/`, and `docs/`. Python code currently lives in `src/agentic_graphrag/` so it can be packaged and imported consistently.

## Evaluation status

Retrieval-only public benchmark results and local answer runs are reported in `eval/README.md`; answer quality remains weak. The public MuSiQue questions and candidate passage corpus are versioned in `eval/data/public/`; the domain evaluation set is frozen in `eval/data/domain/questions_v1.0.jsonl`. The 325-paper inventory remains provisional until full-text relevance and rights review is complete. The local graph pilot, consolidation, candidate generation, audit worksheet preparation, graph retrieval diagnostic, bounded answer evaluation, and one agent wiring query have run; manual labels, Neo4j loading, broader agent evaluation, answer quality work, API serving, and UI deployment remain incomplete.

