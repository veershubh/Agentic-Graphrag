# Evaluation results summary

Generated from the versioned JSON artifacts in `eval/results/` by `python eval/build_results_report.py`. Retrieval values are supporting-document recall; answer values are local model outputs. Samples and corpora differ across tracks, so compare variants only within the same table and track.

## Public benchmark retrieval

| Variant | Questions | 2-hop | 3-hop | 4-hop | Overall R@5 | 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | 300 | 0.575 | 0.403 | 0.310 | 0.429 | 0.400–0.459 |
| dense | 300 | 0.630 | 0.467 | 0.350 | 0.482 | 0.453–0.512 |
| bm25_dense_rrf | 300 | 0.620 | 0.470 | 0.388 | 0.492 | 0.464–0.522 |

Public BM25-only artifact (same frozen 300-question track):

| Variant | Questions | 2-hop | 3-hop | 4-hop | Overall | 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 Okapi | 300 | 0.575 | 0.403 | 0.310 | 0.429 | 0.400–0.459 |

## Domain retrieval diagnostic

| Variant | Questions | 1-hop | 2-hop | 3-hop | Overall R@5 | 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | 98 | 0.816 | 0.450 | 0.311 | 0.549 | 0.474–0.622 |
| graph | 98 | 0.026 | 0.067 | 0.033 | 0.041 | 0.014–0.073 |
| bm25_graph_rrf | 98 | 0.632 | 0.400 | 0.222 | 0.435 | 0.361–0.514 |
| dense | 98 | 0.316 | 0.117 | 0.056 | 0.175 | 0.111–0.247 |
| bm25_dense_graph_rrf | 98 | 0.579 | 0.250 | 0.156 | 0.349 | 0.270–0.430 |
| bm25_dense_rrf | 98 | 0.579 | 0.200 | 0.133 | 0.327 | 0.250–0.405 |

This provisional domain corpus has not completed relevance/rights review; the graph has not passed manual quality audits.

## Answer generation

| Run | Questions | 1-hop F1 | 2-hop F1 | 3-hop F1 | EM | F1 (95% CI) | Citation valid | Mean latency | API cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Public Qwen3 8B, stratified 30 | 30 | 0.243 | 0.161 | 0.244 | 0.100 | 0.216 (0.112–0.335) | 1.000 | 8.4s | $0.00 |
| Domain Qwen3 8B, stratified 30 | 30 | 0.343 | 0.384 | 0.134 | 0.000 | 0.287 (0.207–0.371) | 0.933 | 17.4s | $0.00 |
| Domain agent pilot, 3 total | 3 | 0.167 | 0.419 | 0.080 | 0.000 | 0.222 (0.080–0.419) | 1.000 | 77.4s | $0.00 |

The agent result is a three-question wiring pilot and is not directly comparable as a quality estimate. Faithfulness has not been calibrated against human labels.
