# Evaluation

`eval/data/public/` contains the frozen 300-question MuSiQue slice, its candidate passages, and source manifest. `eval/data/domain/` contains a frozen 109-question set and provisional metadata inventory; full-text paper relevance and rights review remain open. `python eval/run_retrieval_eval.py` runs the public-track BM25 retrieval-only baseline and reports supporting-document recall@k by hop count. Answer generation, answer metrics, dense retrieval, and graph-assisted variants are not yet implemented. Keep the public and domain tracks independent.

## Public BM25 retrieval baseline

The first retrieval-only run used Okapi BM25 (`k1=1.5`, `b=0.75`) over 4,020 candidate passages, with `top_k=5`. Supporting-document recall averages the fraction of gold supporting passages retrieved for each question. Confidence intervals use 10,000 deterministic bootstrap resamples of questions.

| Hop count | Questions | Supporting-document recall@5 | 95% bootstrap CI |
|---:|---:|---:|---:|
| 2 | 100 | 0.575 | 0.520–0.630 |
| 3 | 100 | 0.403 | 0.357–0.447 |
| 4 | 100 | 0.310 | 0.275–0.347 |
| Overall | 300 | 0.429 | 0.400–0.459 |

The detailed run, per-question retrieved passage IDs, settings, and input checksums are versioned in `results/public_bm25_v0.1.json`. This result measures retrieval evidence coverage only; it is not an answer EM/F1 or faithfulness result.
