.PHONY: eval

# Run the deterministic public MuSiQue BM25 baseline. Keep generated output in
# data/processed so this target never rewrites the frozen eval artifacts.
PUBLIC_BM25_OUTPUT ?= data/processed/make_eval_public_bm25.json

eval:
	python eval/run_hybrid_eval.py --bm25-only --output $(PUBLIC_BM25_OUTPUT)
