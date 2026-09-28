# Retrieval

The initial public-track retriever is a dependency-free Okapi BM25 baseline. Run it from the repository root with:

```powershell
python eval/run_retrieval_eval.py
```

It retrieves from the fixed MuSiQue candidate-passage corpus and reports supporting-document recall@k overall and by hop count with deterministic question-level bootstrap confidence intervals. The detailed per-question ranking artifact is written under ignored `data/processed/`. Graph expansion primitives are available in `graph.py`; a domain graph has not yet been built or evaluated. Model cost/latency remain pending. Answer generation and EM/F1 are available through the optional evaluator described in `eval/README.md`. `top_k`, BM25 `k1`/`b`, and bootstrap settings are configured in `configs/default.toml`.

For local domain diagnostics, `python eval/run_hybrid_eval.py --questions eval/data/domain/questions_v1.0.jsonl --passages data/processed/domain_inventory_passages_v1.0.jsonl --output eval/results/domain_inventory_bm25_v0.1.json --bm25-only` runs the same BM25 scorer over the provisional paper inventory without loading the embedding model. See `eval/README.md` for the reported hop-stratified metrics and limitations.

## Dense and hybrid retrieval

Install the optional local embedding dependency with `python -m pip install -e ".[retrieval]"`, then run `python eval/run_hybrid_eval.py`. The command compares BM25, cosine similarity over normalized sentence embeddings, and BM25+dense reciprocal-rank fusion on the same frozen questions. It reports retrieval recall by hop count and bootstrap intervals. The embedding model revision is pinned in `configs/default.toml`; passage embeddings are cached locally under ignored `data/processed/` and reused only when the model revision, passage IDs, and passage content hashes match. This command downloads and runs the configured model locally and makes no paid API calls.

The dense model is [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), an Apache-2.0, 384-dimensional sentence-embedding model. The implementation follows the library's [semantic-search guidance](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html) and uses separate query and document encoders.

## Graph expansion

`retrieval.graph.GraphIndex` performs bounded multi-hop expansion from BM25-matched entity names or caller-supplied entity seeds. It ranks linked passages from node and edge evidence provenance, with configured hop, node, seed, and chunk limits. `FixedHybridRetriever` fuses passage BM25 and graph rankings with RRF; callers can also pass an independently computed dense passage ranking and dense entity seeds. It requires the consolidated node/edge files and local domain passages produced by the graph pipeline. The implementation is available, but an end-to-end graph retrieval evaluation is pending extraction output and a completed graph load/consolidation run.
