# Retrieval

The initial public-track retriever is a dependency-free Okapi BM25 baseline. Run it from the repository root with:

```powershell
python eval/run_retrieval_eval.py
```

It retrieves from the fixed MuSiQue candidate-passage corpus and reports supporting-document recall@k overall and by hop count with deterministic question-level bootstrap confidence intervals. The detailed per-question ranking artifact is written under ignored `data/processed/`. This is a retrieval-only measurement; answer generation, exact match/F1, dense retrieval, graph expansion, and model cost/latency are still pending. `top_k`, BM25 `k1`/`b`, and bootstrap settings are configured in `configs/default.toml`.
