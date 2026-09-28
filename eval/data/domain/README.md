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
python ingest/papers_to_passages.py
python ingest/audit_domain_corpus.py
```

Search rankings change over time. `manifest.json` pins the current reference-list checksum and the candidate snapshot checksum used to produce it. Full text must be reviewed before promoting candidates into the domain corpus. Domain questions must be drafted from raw paper passages, not from the graph.

`questions_draft_v1.0.jsonl` is the current 91-question draft. It carries forward prior items and adds ten comparisons across factuality, medical, software, dialogue, language, security, and visual evaluation. There are 38 one-hop, 30 two-hop, and 21 three-hop answerable questions, plus two verified unanswerable questions (2.2%). The unanswerable share remains below the final target of 10–15%, and the draft is not yet the final 100–150 question set. Resolve its page references locally with `python eval/resolve_domain_evidence.py eval/data/domain/questions_draft_v1.0.jsonl`; generated passage IDs stay under ignored `data/processed/`.

Downloaded PDFs and extracted full text are local working data under ignored `data/raw/` and `data/processed/` directories. The default download count is a 20-paper pilot; `--limit 0` selects the full reference list after the pilot is reviewed. The downloader waits between requests and can resume by skipping existing PDFs. Check each paper's rights before redistributing its PDF or extracted text.

## Acquisition pilot

On 2026-09-28, the first 20 year-balanced candidates produced 19 downloaded PDFs (77,748,729 bytes) and 1,523,554 extracted characters across 364 pages. The subsequent 400-reference local pass recorded 370 PDFs, 30 download failures, 368 extracted records, and 11,784 deterministic passages. Of the extracted records, 350 contain nonempty text, 18 produced no text, and 2 could not be opened; a later corpus audit can reproduce the per-year breakdown from the ignored local manifests. The raw PDFs, full text, passages, and detailed audit output stay under ignored `data/raw/` and `data/processed/` paths. These are ingestion measurements, not model evaluation results. The references and local text still require full-text relevance and rights review before the corpus or QA set can be called frozen.

The downloader resumes by skipping present files. To retry only failed references from its current manifest, use `python ingest/download_arxiv_papers.py --limit 400 --retry-failures`; this preserves the existing manifest and replaces each attempted paper's status. The extraction audit reports counts and IDs only, not paper text.

