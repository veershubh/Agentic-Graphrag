# Problem statement and success measures

## Problem

Multi-hop questions often require evidence spread across several documents. A vector-only retriever can find semantically similar passages while missing explicit links between papers, methods, datasets, and metrics. This project will build and measure a retrieval system that combines dense and keyword retrieval with bounded graph expansion, then uses an agent to select tools for multi-step questions. Answers must cite retrieved evidence and abstain when the corpus does not support an answer.

## Initial scope

The working domain assumption is research papers about LLM evaluation. It is a starting point from the supplied implementation plan, not a fixed requirement. A public multi-hop benchmark will provide a separate credibility track. The evaluation set must be assembled from raw passages and hand-checked before graph construction or agent tuning to reduce circular evaluation.

## Success measures

- Evaluation integrity: frozen, versioned benchmark and domain question files; each answerable item has a checked gold answer and supporting passages, and unanswerable items are tagged.
- Answer quality: exact match and token F1, reported overall and by 1-hop, 2-hop, and 3-hop question groups.
- Evidence quality: supporting-document recall@k and faithfulness, with citation validity checks.
- Practical cost: per-query model cost and p50/p95 latency.
- Research result: compare vector-only, BM25+dense, graph-only, fixed hybrid, and agentic retrieval on the same held-out questions with bootstrap confidence intervals. The central hypothesis is that graph-assisted methods improve multi-hop evidence recall or answer F1 enough to justify their added cost; results may reject that hypothesis.

## Phase 0 acceptance

The local smoke pipeline processes five fixture documents end-to-end without external services, creates stable document and chunk identifiers, and records source metadata in its output. No quality or performance claims will be made from these fixtures.

