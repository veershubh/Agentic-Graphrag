# Domain paper candidates

This is the first bibliography for the planned LLM evaluation research-paper track. It contains 400 arXiv references, balanced at 80 papers per year from 2022 through 2026. The records are marked `candidate_pending_full_text_review`; they are not yet the final frozen paper corpus or a hand-verified QA set.

The references were collected from arXiv's advanced search for papers matching large language model and evaluation/benchmark terms, then ranked using title, abstract, and category signals. The source PDFs and extracted full text stay under ignored `data/raw/` and `data/processed/` paths. Do not redistribute a paper PDF or extracted text without checking that paper's rights. The repository commits only its bibliographic reference, source URLs, and selection audit fields.

To rebuild the current candidate list from arXiv and curate it:

```powershell
python ingest/arxiv_search.py --limit 750 --first-year 2022 --last-year 2026 --output data/raw/arxiv_candidates.jsonl
python ingest/curate_arxiv_candidates.py data/raw/arxiv_candidates.jsonl --per-year 80 --first-year 2022 --last-year 2026
```

Search rankings change over time. `manifest.json` pins the current reference-list checksum and the candidate snapshot checksum used to produce it. Full text must be reviewed before promoting candidates into the domain corpus. Domain questions must be drafted from raw paper passages, not from the graph.

