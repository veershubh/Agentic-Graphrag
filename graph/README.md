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

The default selection covers 20 balanced papers (four per year from 2022–2026) and up to 200 passages; 197 are currently available. The completed default pilot processed all 197 passages with Qwen3 4B. It produced 1,734 entity mentions and 636 accepted triples; ontology and endpoint validation rejected 726 candidate triples. Cached model latency totals 3,189 seconds (about 16.2 seconds per passage), with $0 model API charges. The rejection rate and extraction quality still require human review. The earlier one-passage-per-paper pilot is reproducible with `python graph/extract_domain_graph.py --max-passages-per-paper 1`.

The merger consolidates stable-name nodes, groups repeated relationships while retaining per-chunk evidence, and writes a normalized alias table. On the 197-passage pilot it produced 994 nodes, 581 edges, and 103 unresolved alias collisions, with 627 edge-evidence rows. Alias collisions are emitted separately for review rather than resolved automatically.

`load_neo4j.py` imports the consolidated files in idempotent batches, creates uniqueness constraints, and links each edge's evidence to its source chunk and paper. Preview counts without connecting with `python graph/load_neo4j.py --dry-run`. To load, install `python -m pip install -e ".[neo4j]"`, set `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` (optionally `NEO4J_DATABASE`), then run `python graph/load_neo4j.py`. The database loader has not been run; it does not clear existing data.

`resolve_entity_candidates.py` uses the pinned local sentence-transformer model to rank same-kind name pairs by cosine similarity. Install `python -m pip install -e ".[retrieval]"` and run `python graph/resolve_entity_candidates.py` after consolidation. It writes a review queue with `UNREVIEWED` decisions; it never merges entities automatically. The expanded pilot produced 307 review candidates.

`audit_triples.py` prepares a deterministic random sample of up to 50 edge-evidence rows, including each local source passage, for manual accuracy review. A 50-edge worksheet has been prepared under ignored `data/processed/` so source text is not committed. Fill `reviewer_correct` with `true` or `false`, then score it with `python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl`. Human accuracy labels are still pending.

The graph retrieval diagnostic is versioned in `eval/results/domain_graph_v0.1.json`. On the frozen 98-answerable-question domain track, graph-only supporting recall@5 was 0.041 (95% CI 0.014–0.073); BM25+graph RRF was 0.435 (0.361–0.514), below the BM25 baseline of 0.549 (0.474–0.622). This evaluation uses the expanded 197-passage graph, but it remains a small, unaudited subset of the 325-paper provisional corpus; the results do not support deploying graph expansion yet.

The 50-row extraction audit worksheet and 307-pair entity candidate queue are prepared, but human labels are pending. The Neo4j loader dry run processed the 994-node, 581-edge dataset in nine batches; no database connection or write was made. Human/LLM adjudication, resolution audits, extraction audits, actual Neo4j loading, and scaling beyond the pilot remain future work.
