# Domain paper candidates

This is the candidate bibliography for the LLM evaluation research-paper track. It contains 400 arXiv references, balanced at 80 papers per year from 2022 through 2026. The records are marked `candidate_pending_full_text_review`; the paper corpus still needs full-text relevance and rights review.

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

`questions_v1.0.jsonl` is the frozen domain evaluation set: 109 questions, with 38, 30, and 30 answerable one-, two-, and three-hop items, plus 11 verified unanswerable questions (10.1%). Answerable items include source-page references and resolved passage IDs; every abstention item includes a search audit. Run the full-set validator with `python eval/validate_domain_questions.py eval/data/domain/questions_v1.0.jsonl --require-full-set`. Historical drafts remain in `questions_draft_*.jsonl`.

Downloaded PDFs and extracted full text are local working data under ignored `data/raw/` and `data/processed/` directories. The default download count is a 20-paper pilot; `--limit 0` selects the full reference list after the pilot is reviewed. The downloader waits between requests and can resume by skipping existing PDFs. Check each paper's rights before redistributing its PDF or extracted text.

## Acquisition pilot

On 2026-09-28, the first 20 year-balanced candidates produced 19 downloaded PDFs (77,748,729 bytes) and 1,523,554 extracted characters across 364 pages. The subsequent 400-reference local pass recorded 370 PDFs, 30 download failures, 368 extracted records, and 11,784 deterministic passages. Of the extracted records, 350 contain nonempty text, 18 produced no text, and 2 could not be opened; a later corpus audit can reproduce the per-year breakdown from the ignored local manifests. The raw PDFs, full text, passages, and detailed audit output stay under ignored `data/raw/` and `data/processed/` paths. These are ingestion measurements, not model evaluation results. The question set is frozen; the paper corpus remains a candidate collection pending full-text relevance and rights review.

Two abstention questions request Neo4j implementation details for ORQA and Attributed QA. Neo4j appears in graph-retrieval papers in the candidate corpus, but those papers do not support the details attributed to the named sources.

The downloader resumes by skipping present files. To retry only failed references from its current manifest, use `python ingest/download_arxiv_papers.py --limit 400 --retry-failures`; this preserves the existing manifest and replaces each attempted paper's status. The extraction audit reports counts and IDs only, not paper text.

