"""Freeze a year-balanced reference list from the arXiv search candidate file."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def year_from_id(identifier: str) -> int:
    match = re.match(r"(\d{2})\d{2}\.", identifier)
    if not match:
        raise ValueError(f"Unsupported arXiv ID format: {identifier}")
    return 2000 + int(match.group(1))


def score(record: dict[str, Any]) -> tuple[int, list[str]] | None:
    title = record.get("title", "").lower()
    abstract = record.get("abstract", "").lower()
    text = f"{title} {abstract}"
    if not any(term in text for term in ("large language model", "language model", "llm")):
        return None
    if not any(term in text for term in ("evaluation", "benchmark", "evaluate", "evaluating")):
        return None
    reasons = []
    value = 0
    if any(term in title for term in ("evaluation", "benchmark", "evaluating", "evaluate")):
        value += 5
        reasons.append("evaluation or benchmark in title")
    if "large language model" in text or "language model" in text:
        value += 3
        reasons.append("language model terminology")
    if "llm" in text:
        value += 1
        reasons.append("LLM terminology")
    if any(term in text for term in ("dataset", "metric", "judge", "leaderboard", "assessment")):
        value += 2
        reasons.append("evaluation artifact or method mentioned")
    categories = record.get("categories", "")
    if "cs.CL" in categories or "cs.AI" in categories:
        value += 1
        reasons.append("primary or cross-listed in NLP/AI")
    return value, reasons


def curate(records: list[dict[str, Any]], per_year: int, first_year: int, last_year: int) -> list[dict[str, Any]]:
    groups: dict[int, list[tuple[int, list[str], dict[str, Any]]]] = defaultdict(list)
    for record in records:
        year = year_from_id(record["arxiv_id"])
        if not first_year <= year <= last_year:
            continue
        ranked = score(record)
        if ranked is not None:
            groups[year].append((ranked[0], ranked[1], record))
    selected = []
    for year in range(first_year, last_year + 1):
        candidates = sorted(
            groups[year],
            key=lambda item: (-item[0], item[2]["arxiv_id"]),
        )[:per_year]
        if len(candidates) < per_year:
            raise ValueError(f"Year {year} has {len(candidates)} relevant records; need {per_year}")
        for relevance_score, reasons, record in candidates:
            selected.append(
                {
                    "arxiv_id": record["arxiv_id"],
                    "title": record["title"],
                    "authors": record["authors"],
                    "year": year,
                    "categories": record["categories"],
                    "abstract_url": record["abstract_url"],
                    "pdf_url": record["pdf_url"],
                    "search_query": record["search_query"],
                    "selection_score": relevance_score,
                    "selection_reasons": reasons,
                    "review_status": "candidate_pending_full_text_review",
                }
            )
    selected.sort(key=lambda item: (item["year"], item["arxiv_id"]))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--per-year", type=int, default=80)
    parser.add_argument("--first-year", type=int, default=2022)
    parser.add_argument("--last-year", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=Path("eval/data/domain/papers_candidates.jsonl"))
    args = parser.parse_args()

    records = [json.loads(line) for line in args.candidates.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = curate(records, args.per_year, args.first_year, args.last_year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected), encoding="utf-8")
    print(f"Selected {len(selected)} references from {len(records)} search candidates")
    print(f"Years: {dict(sorted(Counter(row['year'] for row in selected).items()))}")
    print(f"Candidate input SHA-256: {sha256(args.candidates)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()

