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
```

The default selection covers 20 papers and at most 200 passages. The runner makes paid model calls for cache misses. No extraction calls have been run yet; cost and extraction quality therefore remain unmeasured. Add current input and output token rates under `[graph.extraction]` in `configs/default.toml` to enable a cost estimate in its summary.

Entity resolution beyond normalized-name matching, Neo4j storage, extraction audits, and scaling beyond the pilot remain future work.
