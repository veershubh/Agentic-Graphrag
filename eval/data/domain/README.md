# Domain paper candidates

This is the first bibliography for the planned LLM evaluation research-paper track. It contains 400 arXiv references, balanced at 80 papers per year from 2022 through 2026. The records are marked `candidate_pending_full_text_review`; they are not yet the final frozen paper corpus or a hand-verified QA set.

The references were collected from arXiv's advanced search for papers matching large language model and evaluation/benchmark terms, then ranked using title, abstract, and category signals. The source PDFs and extracted full text stay under ignored `data/raw/` and `data/processed/` paths. Do not redistribute a paper PDF or extracted text without checking that paper's rights. The repository commits only its bibliographic reference, source URLs, and selection audit fields.

To rebuild the current candidate list from arXiv and curate it:

```powershell
python ingest/arxiv_search.py --limit 750 --first-year 2022 --last-year 2026 --output data/raw/arxiv_candidates.jsonl
python ingest/curate_arxiv_candidates.py data/raw/arxiv_candidates.jsonl --per-year 80 --first-year 2022 --last-year 2026
python ingest/download_arxiv_papers.py --limit 20
python -m pip install -e ".[papers]"
python ingest/extract_arxiv_papers.py
```

Search rankings change over time. `manifest.json` pins the current reference-list checksum and the candidate snapshot checksum used to produce it. Full text must be reviewed before promoting candidates into the domain corpus. Domain questions must be drafted from raw paper passages, not from the graph.

Downloaded PDFs and extracted full text are local working data under ignored `data/raw/` and `data/processed/` directories. The default download count is a 20-paper pilot; `--limit 0` selects the full reference list after the pilot is reviewed. The downloader waits between requests and can resume by skipping existing PDFs. Check each paper's rights before redistributing its PDF or extracted text.

## Acquisition pilot

On 2026-09-28, the first 20 year-balanced candidates produced 19 downloaded PDFs (77,748,729 bytes) and 1,523,554 extracted characters across 364 pages. One source returned HTTP 406. This estimates local storage at roughly 1.6 GB for 400 papers; the full acquisition is running locally and logs each success or failure in the ignored download manifest. These are ingestion measurements, not model evaluation results.

