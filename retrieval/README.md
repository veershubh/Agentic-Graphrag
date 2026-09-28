# Retrieval

The initial public-track retriever is a dependency-free Okapi BM25 baseline. Run it from the repository root with:

```powershell
python eval/run_retrieval_eval.py
```

It retrieves from the fixed MuSiQue candidate-passage corpus and reports supporting-document recall@k overall and by hop count with deterministic question-level bootstrap confidence intervals. The detailed per-question ranking artifact is written under ignored `data/processed/`. This is a retrieval-only measurement; answer generation, exact match/F1, graph expansion, and model cost/latency are still pending. `top_k`, BM25 `k1`/`b`, and bootstrap settings are configured in `configs/default.toml`.

## Dense and hybrid retrieval

Install the optional local embedding dependency with `python -m pip install -e ".[retrieval]"`, then run `python eval/run_hybrid_eval.py`. The command compares BM25, cosine similarity over normalized sentence embeddings, and BM25+dense reciprocal-rank fusion on the same frozen questions. It reports retrieval recall by hop count and bootstrap intervals. The embedding model revision is pinned in `configs/default.toml`; passage embeddings are cached locally under ignored `data/processed/` and reused only when the model revision, passage IDs, and passage content hashes match. This command downloads and runs the configured model locally and makes no paid API calls.

The dense model is [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), an Apache-2.0, 384-dimensional sentence-embedding model. The implementation follows the library's [semantic-search guidance](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html) and uses separate query and document encoders.
