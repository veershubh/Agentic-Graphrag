# Evaluation

`eval/data/public/` contains the frozen 300-question MuSiQue slice, its candidate passages, and source manifest. `eval/data/domain/` contains a frozen 109-question set and provisional metadata inventory; full-text paper relevance and rights review remain open. `python eval/run_retrieval_eval.py` runs the BM25 retrieval-only baseline. `python eval/run_hybrid_eval.py` compares BM25, dense, and BM25+dense RRF retrieval on the same public slice. The answer evaluator uses local Ollama; its first 30-question run is recorded below. Faithfulness judging and graph-assisted answer variants remain future work. Keep the public and domain tracks independent.

## Initial local answer run

The same first 30 two-hop questions were run with two local models over identical BM25+dense RRF passages. Qwen3 4B abstained on all 30 (EM 0.000, F1 0.000, mean latency 1.87s). Qwen3 8B abstained on 11, answered 19, and achieved EM 0.067 and mean F1 0.165 (mean latency 6.48s, p95 8.78s). Abstentions are normalized to empty answers and citation lists; the resulting citation-validity rate was 1.00. Both runs had $0.00 model API cost. Qwen3 8B is now the answer default, while extraction/planning stay on 4B. This is a small early sample, and answer quality remains poor; the 8B model also has higher local memory and latency needs. Full records are in `results/public_answer_qwen3_4b_v0.1.json` and `results/public_answer_qwen3_8b_v0.1.json`.

Once graph extraction and consolidation have produced local node and edge files, `python eval/run_graph_eval.py` compares graph-only and BM25+graph RRF on the frozen domain questions. Add `--include-dense` to also compare dense-only and BM25+dense+graph RRF; dense domain encoding may be slow on CPU. The runner reports hop-stratified supporting recall, bootstrap intervals, paired comparisons, and input hashes. It has been run on the initial 20-passage local graph pilot; see the result below and the caveat in `../graph/README.md`.

## Initial local graph pilot

The 20-passage graph (one passage from each of 20 balanced papers) was evaluated against the 98 answerable questions in the domain set. Supporting-document recall@5 was 0.071 for graph-only (95% CI 0.037–0.109), 0.457 for BM25+graph RRF (0.379–0.536), and 0.549 for BM25 (0.474–0.622). The hybrid was below BM25 on this sample. This is an early diagnostic from an unaudited graph with 58 of 145 candidate triples rejected by validation; it does not support a claim that graph retrieval helps. Full per-question results and input hashes are in `results/domain_graph_v0.1.json`.

`.github/workflows/retrieval-eval.yml` runs the dependency-free public BM25 evaluation on retrieval-related pull requests, nightly, or manually. It enforces conservative overall and per-hop recall floors. This gate covers retrieval only; it does not evaluate generated answers, faithfulness, graph retrieval, or agent behavior.

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

`python eval/run_answer_eval.py` uses the selected retriever's top-5 passages and local Ollama inference to generate citation-backed answers. It defaults to 30 questions; pass `--limit 0` to run the full remaining set, or use `--offset` for a bounded slice. Start Ollama and pull `qwen3:4b-instruct` first. The script measures exact match, token F1, citation validity, supporting recall, latency, and token usage, with zero model API charges. It writes progress after each question to ignored `data/processed/`; no generated answer metrics are included in this repository yet. Because the local model is smaller than the model originally configured for the answer stage, report its identity with results and audit answer quality before drawing broader conclusions.
