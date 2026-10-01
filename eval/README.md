# Evaluation

`eval/data/public/` contains the frozen 300-question MuSiQue slice, its candidate passages, and source manifest. `eval/data/domain/` contains a frozen 109-question set and provisional metadata inventory; full-text paper relevance and rights review remain open. `python eval/run_retrieval_eval.py` runs the BM25 retrieval-only baseline. `python eval/run_hybrid_eval.py` compares BM25, dense, and BM25+dense RRF retrieval on the same public slice. The answer evaluator uses local Ollama and accepts ranking keys saved by either the hybrid or graph evaluator, including fixed graph hybrid variants. Faithfulness judging remains future work. Keep the public and domain tracks independent.

Build a combined Markdown snapshot from the checked-in artifacts with `python eval/build_results_report.py`; it writes `eval/results-summary.md` and does not run retrieval or call a model. The report intentionally labels the provisional domain and three-question agent pilot so small or unaudited samples are not mistaken for final results.

## Initial local answer run

The same first 30 two-hop questions were run with two local models over identical BM25+dense RRF passages. Qwen3 4B abstained on all 30 (EM 0.000, F1 0.000, mean latency 1.87s). Qwen3 8B abstained on 11, answered 19, and achieved EM 0.067 and mean F1 0.165 (mean latency 6.48s, p95 8.78s). Abstentions are normalized to empty answers and citation lists; the resulting citation-validity rate was 1.00. Both runs had $0.00 model API cost. Qwen3 8B is now the answer default, while extraction/planning stay on 4B. Full matched-sample records are in `results/public_answer_qwen3_4b_v0.1.json` and `results/public_answer_qwen3_8b_v0.1.json`.

A second Qwen3 8B run used 10 questions from each hop bucket, with identical BM25+dense RRF retrieval. It achieved overall EM 0.100, F1 0.216, and mean latency 8.45s; the 95% question-bootstrap interval for F1 is 0.112–0.335. This confirms some correct answers but remains low quality on a small sample.

| Hops | Questions | EM | Token F1 | Supporting recall@5 | Mean latency |
|---:|---:|---:|---:|---:|---:|
| 2 | 10 | 0.100 | 0.243 | 0.700 | 6.91s |
| 3 | 10 | 0.100 | 0.161 | 0.500 | 10.30s |
| 4 | 10 | 0.100 | 0.244 | 0.375 | 8.14s |

The stratified sample and per-question outputs are in `results/public_answer_qwen3_8b_stratified_v0.1.json`; it uses source record offsets 0, 100, and 200, not a random sample. The larger model has higher local memory and latency needs. All runs have zero model API cost.

Once graph extraction and consolidation have produced local node and edge files, `python eval/run_graph_eval.py` compares graph-only and BM25+graph RRF on the frozen domain questions. Add `--include-dense` to compare dense-only, BM25+dense, and both lexical- and dense-entity-seeded graph expansion variants. Dense passage and entity vectors run locally; first-time encoding may be slow on CPU. The runner reports hop-stratified supporting recall, bootstrap intervals, paired comparisons, and input hashes. Results on the expanded 197-passage graph pilot include `results/domain_graph_dense_entity_seed_v0.1.json`; see the caveat in `../graph/README.md`.

## Initial local graph pilot

The expanded graph (197 passages from 20 balanced papers) was evaluated against the 98 answerable questions in the domain set. Supporting-document recall@5 was 0.041 for graph-only (95% CI 0.014–0.073), 0.435 for BM25+graph RRF (0.361–0.514), and 0.549 for BM25 (0.474–0.622). The hybrid was below BM25, with a paired recall difference of -0.114 (95% CI -0.179 to -0.054). This is a diagnostic from an unaudited graph with 726 of 1,362 candidate triples rejected by validation; it does not support a claim that graph retrieval helps. Full per-question results and input hashes are in `results/domain_graph_v0.1.json`. The corpus covers only 20 papers from a provisional 325-paper inventory.

## Domain retrieval ablations

The same 98 answerable questions were used for BM25, local dense, hybrid, and graph comparisons. Dense vectors reused the exact 10,878-passage cache from the agent pilot (`sentence-transformers/all-MiniLM-L6-v2`, pinned revision). Every number is supporting-document recall@5; intervals and paired comparisons are in the machine-readable artifacts.

| Variant | Recall@5 | Paired difference vs BM25 (95% CI) |
|---|---:|---:|
| BM25 | 0.549 | — |
| Dense | 0.175 | -0.374 (-0.457 to -0.291) |
| BM25 + dense RRF | 0.327 | -0.223 (-0.294 to -0.151) |
| Graph only | 0.041 | -0.509 (-0.587 to -0.430) |
| BM25 + graph RRF | 0.435 | -0.114 (-0.179 to -0.054) |
| BM25 + dense + graph RRF | 0.349 | -0.201 (-0.276 to -0.128) |

The expanded graph does not improve recall on this question set, and adding dense rankings or both dense and graph rankings also lowers recall. These are negative retrieval results for this provisional domain corpus, not a universal comparison of the methods. Full results: `results/domain_dense_v0.1.json` and `results/domain_graph_dense_v0.1.json`.

The graph-depth/top-k sweep changes one setting at a time. At top-5, graph depth 1 and 2 gave the same measured recalls with the current seed, node, and chunk limits. Lowering the cutoff to 3 lowers absolute recall for all variants; increasing it to 10 raises recall, while BM25+graph remains below BM25. See `results/domain_graph_hops1_k5_v0.1.json`, `results/domain_graph_hops2_k3_v0.1.json`, and `results/domain_graph_hops2_k10_v0.1.json`.

| Graph hops | Top-k | BM25 | Graph only | BM25 + graph RRF |
|---:|---:|---:|---:|---:|
| 1 | 5 | 0.549 | 0.041 | 0.435 |
| 2 | 5 | 0.549 | 0.041 | 0.435 |
| 2 | 3 | 0.442 | 0.019 | 0.313 |
| 2 | 10 | 0.713 | 0.071 | 0.575 |

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

`python eval/run_answer_eval.py` uses the selected retriever's top-5 passages and local Ollama inference to generate citation-backed answers. It defaults to 30 questions; pass `--limit 0` to run the full selected set, or use `--offset` for a bounded slice. Start Ollama and pull the configured answer model (`qwen3:8b`). The script measures exact match, token F1, citation validity, supporting recall, latency, and token usage, with zero model API charges. It writes progress after each question to ignored `data/processed/`; a bounded domain sample is reported below. Because the local model is smaller than the model originally configured for the answer stage, report its identity with results and audit answer quality before drawing broader conclusions.

Run the answer evaluator on the fixed-hybrid domain rankings and the same 30-question stratified sample used by the BM25 answer baseline with:

```powershell
python eval/run_answer_eval.py --questions eval/data/domain/questions_answer_eval_stratified_v0.1.jsonl --passages data/processed/domain_inventory_passages_v1.0.jsonl --retrieval-results eval/results/domain_graph_dense_entity_seed_v0.1.json --retriever bm25_dense_entity_graph_rrf --output data/processed/domain_fixed_hybrid_answer_eval_v0.1.json --limit 0
```

On the completed sample, fixed-hybrid token F1 was 0.289 (95% bootstrap CI 0.219–0.361), versus 0.287 (0.207–0.371) for the BM25 answer baseline. The paired difference was +0.002 (95% CI -0.074 to +0.080); this small sample provides no evidence of an answer-quality improvement. Supporting recall on those same 30 questions was 0.244 for fixed hybrid versus 0.556 for BM25. The fixed-hybrid answer-generation time averaged 16.1s; retrieval was precomputed. The versioned run is `results/domain_fixed_hybrid_answer_qwen3_8b_v0.1.json`, and the paired comparison is in `results-summary.md`.

## Domain local answer sample

The domain answer evaluator uses Qwen3 8B with local Ollama and the top-five BM25 passages. The deterministic sample is the first ten answerable items from each hop bucket in `data/domain/questions_answer_eval_stratified_v0.1.jsonl`; it is not a random sample. Overall EM was 0.000 and token F1 was 0.287 (95% bootstrap CI 0.207–0.371). Citation validity was 0.933, but gold citation precision/recall averaged 0.237/0.289. BM25's retrieved supporting-document recall on these 30 items was 0.556. Mean latency was 17.38s, p95 was 22.69s, and mean API cost was $0.00; one structured-output retry took 127.54s. Four questions were answered with abstentions. These metrics show weak exact-answer quality despite some token overlap and high within-retrieval citation validity.

| Hops | Questions | EM | Token F1 (95% CI) | Citation validity | Supporting recall@5 | Mean latency |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 0.000 | 0.343 (0.230–0.593) | 1.000 | 0.800 | 9.61s |
| 2 | 10 | 0.000 | 0.384 (0.238–0.497) | 0.800 | 0.500 | 15.29s |
| 3 | 10 | 0.000 | 0.134 (0.037–0.198) | 1.000 | 0.367 | 27.25s |

The stratified questions, per-question answers, scores, citation IDs, and checksums are versioned in `data/domain/questions_answer_eval_stratified_v0.1.jsonl` and `results/domain_answer_qwen3_8b_stratified_v0.1.json`. Faithfulness has not been evaluated by a calibrated judge.

Reproduce the answer run with locally ingested domain passages using:

```powershell
python eval/run_answer_eval.py --questions eval/data/domain/questions_answer_eval_stratified_v0.1.jsonl --passages data/processed/domain_inventory_passages_v1.0.jsonl --retrieval-results eval/results/domain_inventory_bm25_v0.1.json --retriever bm25 --output data/processed/domain_answer_eval_stratified_v0.1.json --limit 0
```

## Agentic retrieval pilot

The bounded agent was evaluated on one frozen answerable question per hop bucket (questions `domain-0001`, `domain-0021`, and `domain-0023`). Token F1 was 0.222, exact match 0.000, valid citations 1.000, and supporting recall@5 0.667. Mean end-to-end latency was 77.4s, compared with 14.4s for BM25 answer generation on those same questions; local model API cost was $0.00 for both. The sample is too small for a quality conclusion, and the agent did not improve answer F1 over BM25 on these three examples.

| System | Questions | Exact match | Token F1 | Valid citations | Supporting recall@5 | Mean latency |
|---|---:|---:|---:|---:|---:|---:|
| BM25 + Qwen3 8B answerer | 3 | 0.000 | 0.315 | 1.000 | 0.611 | 14.4s |
| Planner + keyword/vector/graph tools + Qwen3 8B | 3 | 0.000 | 0.222 | 1.000 | 0.667 | 77.4s |

The selected questions, answer metrics, step counts, stop reasons, retrieval IDs, and input hashes are in `data/domain/questions_agent_eval_pilot_v0.1.jsonl` and `results/domain_agent_qwen3_8b_pilot_v0.1.json`. Reproduce it with `python eval/run_agent_eval.py --per-hop 1 --output data/processed/domain_agent_eval_pilot.json`. This command requires local domain passages, graph files, the embedding cache/model, and Ollama.

## Unanswerable abstention probe

Qwen3 8B with top-five BM25 passages was run against all 11 verified unanswerable questions. The end-to-end system abstained on 7/11 (63.6%) and produced answers on 4/11 (36.4%). Two malformed, truncated model responses were converted to safe abstentions after retries; excluding those failures, the answerer itself abstained on 5/9 (55.6%). Thus citation-format validation alone does not prevent unsupported answers, and abstention is not reliable yet. Citation validity was 1.000, which only means emitted IDs were among the retrieved passages; it does not mean those passages support a claim. The deterministic questions, retrievals, outputs, failure flags, and hashes are in `data/domain/questions_unanswerable_v1.0.jsonl`, `results/domain_unanswerable_bm25_v0.1.json`, and `results/domain_unanswerable_qwen3_8b_v0.1.json`. Model API cost was $0.00; the longest response including retries took about 161s.

We checked whether BM25's highest passage score could serve as a simple answerability cutoff. Answerable top scores ranged 17.24–68.07 and unanswerable scores ranged 18.98–39.71 (AUC 0.786). A threshold high enough to reject all 11 unanswerable probes retained only 45.9% of answerable questions. This exploratory in-sample result does not support deploying a score cutoff; it would block more than half of answerable queries and still needs independent validation. Reproduce with `python eval/analyze_retrieval_abstention.py`; detailed sweep is in `results/domain_abstention_threshold_v0.1.json`.

Reproduce the two stages with:

```powershell
python eval/run_hybrid_eval.py --questions eval/data/domain/questions_unanswerable_v1.0.jsonl --passages data/processed/domain_inventory_passages_v1.0.jsonl --output eval/results/domain_unanswerable_bm25_v0.1.json --bm25-only --include-unanswerable
python eval/run_answer_eval.py --questions eval/data/domain/questions_unanswerable_v1.0.jsonl --passages data/processed/domain_inventory_passages_v1.0.jsonl --retrieval-results eval/results/domain_unanswerable_bm25_v0.1.json --retriever bm25 --output data/processed/domain_unanswerable_answer_eval_v0.1.json --limit 0
```
