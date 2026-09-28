# Evaluation

`eval/data/public/` contains the frozen 300-question MuSiQue slice, its candidate passages, and source manifest. `eval/data/domain/` contains a frozen 109-question set and provisional metadata inventory; full-text paper relevance and rights review remain open. `python eval/run_retrieval_eval.py` runs the BM25 retrieval-only baseline. `python eval/run_hybrid_eval.py` compares BM25, dense, and BM25+dense RRF retrieval on the same public slice. The bounded answer evaluator is available, but no API-backed answer run is recorded yet; faithfulness judging and graph-assisted variants remain future work. Keep the public and domain tracks independent.

## Public BM25 retrieval baseline

The first retrieval-only run used Okapi BM25 (`k1=1.5`, `b=0.75`) over 4,020 candidate passages, with `top_k=5`. Supporting-document recall averages the fraction of gold supporting passages retrieved for each question. Confidence intervals use 10,000 deterministic bootstrap resamples of questions.

| Hop count | Questions | Supporting-document recall@5 | 95% bootstrap CI |
|---:|---:|---:|---:|
| 2 | 100 | 0.575 | 0.520–0.630 |
| 3 | 100 | 0.403 | 0.357–0.447 |
| 4 | 100 | 0.310 | 0.275–0.347 |
| Overall | 300 | 0.429 | 0.400–0.459 |

The detailed run, per-question retrieved passage IDs, settings, and input checksums are versioned in `results/public_bm25_v0.1.json`. This result measures retrieval evidence coverage only; it is not an answer EM/F1 or faithfulness result.

## Dense and hybrid comparison

This run used a locally cached, revision-pinned `sentence-transformers/all-MiniLM-L6-v2` model and the same 300 questions and 4,020 passages. The hybrid uses reciprocal-rank fusion over the top 50 candidates from each retriever (`rrf_k=60`) and evaluates the fused top 5.

| Variant | 2-hop recall@5 | 3-hop recall@5 | 4-hop recall@5 | Overall recall@5 |
|---|---:|---:|---:|---:|
| BM25 | 0.575 | 0.403 | 0.310 | 0.429 |
| Dense | 0.630 | 0.467 | 0.350 | 0.482 |
| BM25 + dense RRF | 0.620 | 0.470 | 0.388 | 0.492 |

The paired question-bootstrap 95% interval for the overall RRF-minus-BM25 difference is +0.042 to +0.084 (mean +0.063). The per-variant intervals and paired differences by hop are in `results/public_hybrid_v0.1.json`. This is retrieval evidence coverage only and does not measure answer correctness. The local embedding model and cache are described in `../retrieval/README.md`.

## Domain corpus BM25 diagnostic

The current provisional inventory was evaluated with BM25 over 10,878 local passages from 325 papers. The 11 unanswerable probes are excluded from support recall; the run does not yet score abstention behavior. All 57 unique cited evidence-source papers are present. Because full-text relevance and rights screening is still pending, treat this as a diagnostic rather than a final domain benchmark result.

| Hop count | Questions | Supporting-document recall@5 | 95% bootstrap CI |
|---:|---:|---:|---:|
| 1 | 38 | 0.816 | 0.684–0.921 |
| 2 | 30 | 0.450 | 0.350–0.550 |
| 3 | 30 | 0.311 | 0.244–0.378 |
| Overall | 98 | 0.549 | 0.474–0.622 |

Rebuild the locally filtered passage file and rerun BM25 with:

```powershell
python ingest/build_domain_corpus_inventory.py
python eval/run_hybrid_eval.py --questions eval/data/domain/questions_v1.0.jsonl --passages data/processed/domain_inventory_passages_v1.0.jsonl --output eval/results/domain_inventory_bm25_v0.1.json --bm25-only
```

The versioned run artifact contains question IDs, retrieved passage IDs, scores, and input checksums only; passage text remains in ignored local working data.

## Answer generation evaluator

`python eval/run_answer_eval.py` uses the selected retriever's top-5 passages and the OpenAI [Responses API](https://developers.openai.com/api/docs/guides/text) with [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) to generate answers with citations. It defaults to 30 questions; pass `--limit 0` to run the full remaining set, or use `--offset` for a bounded slice. Install the optional SDK with `python -m pip install -e ".[api]"` and provide `OPENAI_API_KEY` in the environment before running. The script measures exact match, token F1, citation validity, supporting recall, latency, and token usage. It writes progress after each question to ignored `data/processed/`; no API calls or generated answer metrics are included in this repository yet. Cost is reported only when current input and output token rates are supplied in the config.
