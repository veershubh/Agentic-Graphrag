# Graph construction

The default model is [`qwen3:4b-instruct`](https://ollama.com/library/qwen3%3A4b-instruct) served locally by Ollama. The Q4_K_M model is about 2.5 GB and Apache 2.0 licensed; local inference avoids per-token API charges. Structured JSON schemas are sent to Ollama's [local chat API](https://docs.ollama.com/capabilities/structured-outputs). This 4B quantized model is a lower-resource choice; its extraction accuracy must be measured with the included manual audit before scaling.

The Phase 3 scaffold defines a constrained ontology in `ontology.py`:

- Entities: `Paper`, `Method`, `Dataset`, `Metric`, and `Task`.
- Relations: `PROPOSES`, `EVALUATES_ON`, `USES`, `OUTPERFORMS`, and `CITES`.
- Stable IDs are derived from entity kind and normalized name. Extracted edges retain their source chunk and paper IDs.
- Relation endpoint types are checked, and ambiguous aliases are rejected instead of being resolved arbitrarily.

`extract_domain_graph.py` runs a deterministic, year-balanced pilot over the provisional paper inventory. By default it selects four papers per year and up to ten passages per paper. It requests strict structured output, ignores instructions embedded in passage text, and caches each response by prompt version, model, passage ID, and passage content hash. Cache, extraction, and summary files are written under ignored `data/processed/`; they contain extraction records and provenance, not passage text.

The graph extractor uses the local Ollama runtime and makes no paid API calls. Pull the model once, then run the pilot:

```powershell
ollama pull qwen3:4b-instruct
python ingest/build_domain_corpus_inventory.py
python graph/extract_domain_graph.py
python graph/merge_graph_extractions.py
```

The default selection covers 20 papers and at most 200 passages (197 are currently available in the local selection). The initial bounded pilot used `--max-passages-per-paper 1`, so it processed 20 passages across four papers per year from 2022–2026. Qwen3 produced 175 entity records and 145 candidate triples; ontology and endpoint validation accepted 87 triples and rejected 58. It took 255 seconds of sequential model time (about 12.8 seconds per passage) and had zero model API charges. The high rejection rate means these extractions need review before scaling. Reproduce with `python graph/extract_domain_graph.py --max-passages-per-paper 1`.

The merger consolidates stable-name nodes, groups repeated relationships while retaining per-chunk evidence, and writes a normalized alias table. On the initial pilot it produced 173 nodes, 87 edges, and 19 unresolved alias collisions. Alias collisions are emitted separately for review rather than resolved automatically.

`load_neo4j.py` imports the consolidated files in idempotent batches, creates uniqueness constraints, and links each edge's evidence to its source chunk and paper. Preview counts without connecting with `python graph/load_neo4j.py --dry-run`. To load, install `python -m pip install -e ".[neo4j]"`, set `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` (optionally `NEO4J_DATABASE`), then run `python graph/load_neo4j.py`. The database loader has not been run; it does not clear existing data.

`resolve_entity_candidates.py` uses the pinned local sentence-transformer model to rank same-kind name pairs by cosine similarity. Install `python -m pip install -e ".[retrieval]"` and run `python graph/resolve_entity_candidates.py` after consolidation. It writes a review queue with `UNREVIEWED` decisions; it never merges entities automatically. The initial pilot produced 12 review candidates.

`audit_triples.py` prepares a deterministic random sample of up to 50 edge-evidence rows, including each local source passage, for manual accuracy review. A 50-edge worksheet has been prepared under ignored `data/processed/` so source text is not committed. Fill `reviewer_correct` with `true` or `false`, then score it with `python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl`. Human accuracy labels are still pending.

The first graph retrieval diagnostic is versioned in `eval/results/domain_graph_v0.1.json`. On the frozen 98-answerable-question domain track, graph-only supporting recall@5 was 0.071 (95% CI 0.037–0.109); BM25+graph RRF was 0.457 (0.379–0.536), below the BM25 baseline of 0.549 (0.474–0.622). The sample contains one passage per paper and is intentionally too small to judge a full graph; these results do not support deploying graph expansion yet.

Human/LLM adjudication, resolution audits, extraction audits, and scaling beyond the pilot remain future work.
