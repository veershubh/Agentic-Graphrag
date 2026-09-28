# Graph construction

The Phase 3 scaffold defines a constrained ontology in `ontology.py`:

- Entities: `Paper`, `Method`, `Dataset`, `Metric`, and `Task`.
- Relations: `PROPOSES`, `EVALUATES_ON`, `USES`, `OUTPERFORMS`, and `CITES`.
- Stable IDs are derived from entity kind and normalized name. Extracted edges retain their source chunk and paper IDs.
- Relation endpoint types are checked, and ambiguous aliases are rejected instead of being resolved arbitrarily.

`extract_domain_graph.py` runs a deterministic, year-balanced pilot over the provisional paper inventory. By default it selects four papers per year and up to ten passages per paper. It requests strict structured output, ignores instructions embedded in passage text, and caches each response by prompt version, model, passage ID, and passage content hash. Cache, extraction, and summary files are written under ignored `data/processed/`; they contain extraction records and provenance, not passage text.

To run the pilot after setting `OPENAI_API_KEY` and installing the optional API dependency:

```powershell
python -m pip install -e ".[api]"
python ingest/build_domain_corpus_inventory.py
python graph/extract_domain_graph.py
python graph/merge_graph_extractions.py
```

The default selection covers 20 papers and at most 200 passages. The runner makes paid model calls for cache misses. No extraction calls have been run yet; cost and extraction quality therefore remain unmeasured. Add current input and output token rates under `[graph.extraction]` in `configs/default.toml` to enable a cost estimate in its summary.

The merger consolidates stable-name nodes, groups repeated relationships while retaining per-chunk evidence, and writes a normalized alias table. Alias collisions are emitted separately for later review rather than resolved automatically. The merger also has not been run because there are no extraction records yet.

`load_neo4j.py` imports the consolidated files in idempotent batches, creates uniqueness constraints, and links each edge's evidence to its source chunk and paper. Preview counts without connecting with `python graph/load_neo4j.py --dry-run`. To load, install `python -m pip install -e ".[neo4j]"`, set `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` (optionally `NEO4J_DATABASE`), then run `python graph/load_neo4j.py`. The database loader has not been run; it does not clear existing data.

Embedding-based duplicate candidates, human/LLM adjudication, resolution audits, extraction audits, and scaling beyond the pilot remain future work.
