"""Summarize local paper acquisition and extraction coverage without printing paper text."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(
    references: list[dict[str, Any]],
    downloads: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    extraction_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    ref_by_id = {str(row["arxiv_id"]): row for row in references}
    # Keep the last status in case a later retry superseded an earlier failure.
    download_by_id = {str(row["arxiv_id"]): row for row in downloads}
    paper_by_id = {str(row["arxiv_id"]): row for row in papers}

    download_years: dict[int, Counter[str]] = defaultdict(Counter)
    for identifier, result in download_by_id.items():
        reference = ref_by_id.get(identifier, result)
        download_years[int(reference["year"])][str(result.get("status", "unknown"))] += 1

    extraction_years: dict[int, Counter[str]] = defaultdict(Counter)
    for identifier, paper in paper_by_id.items():
        reference = ref_by_id.get(identifier, paper)
        year = int(reference["year"])
        extraction_years[year]["papers"] += 1
        extraction_years[year]["pages"] += int(paper.get("page_count", 0))
        extraction_years[year]["characters"] += int(paper.get("character_count", 0))
        if int(paper.get("character_count", 0)) == 0:
            extraction_years[year]["empty_text"] += 1
    for failure in extraction_failures:
        identifier = str(failure["arxiv_id"])
        reference = ref_by_id.get(identifier, failure)
        extraction_years[int(reference["year"])]["failures"] += 1

    extracted_ids = set(paper_by_id)
    downloaded_ids = {
        identifier
        for identifier, result in download_by_id.items()
        if result.get("status") in {"downloaded", "already_present"}
    }
    missing_extractions = sorted(downloaded_ids - extracted_ids)
    years = sorted({int(row["year"]) for row in references})
    return {
        "reference_count": len(references),
        "download_manifest_entries": len(downloads),
        "download_status_totals": dict(sorted(Counter(str(row.get("status", "unknown")) for row in downloads).items())),
        "download_coverage_by_year": {
            str(year): dict(sorted(download_years[year].items())) for year in years
        },
        "extraction_by_year": {
            str(year): dict(sorted(extraction_years[year].items())) for year in years
        },
        "extracted_paper_count": len(papers),
        "extracted_page_count": sum(int(row.get("page_count", 0)) for row in papers),
        "extracted_character_count": sum(int(row.get("character_count", 0)) for row in papers),
        "extraction_failure_count": len(extraction_failures),
        "extraction_failure_ids": sorted(str(row["arxiv_id"]) for row in extraction_failures),
        "empty_text_paper_ids": sorted(
            str(row["arxiv_id"]) for row in papers if int(row.get("character_count", 0)) == 0
        ),
        "downloaded_but_not_extracted_ids": missing_extractions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, default=Path("eval/data/domain/papers_candidates.jsonl"))
    parser.add_argument("--downloads", type=Path, default=Path("data/raw/paper_downloads.jsonl"))
    parser.add_argument("--papers", type=Path, default=Path("data/processed/domain_papers.jsonl"))
    parser.add_argument("--extraction-failures", type=Path, default=Path("data/processed/domain_papers_failures.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/domain_corpus_audit.json"))
    args = parser.parse_args()

    references = read_jsonl(args.references)
    if not references:
        raise SystemExit(f"No paper references found in {args.references}")
    report = audit(references, read_jsonl(args.downloads), read_jsonl(args.papers), read_jsonl(args.extraction_failures))
    report["references_sha256"] = sha256(args.references)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Audit written to {args.output}")


if __name__ == "__main__":
    main()
