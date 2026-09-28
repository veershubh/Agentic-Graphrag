"""Resolve page/chunk references in draft questions to stable passage IDs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def resolve(questions: list[dict[str, Any]], passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (passage["arxiv_id"], passage["page_number"], passage["page_chunk_index"]): passage
        for passage in passages
    }
    resolved = []
    for question in questions:
        refs = question.pop("supporting_evidence_refs", [])
        supports = []
        source_papers = []
        for ref in refs:
            key = (ref["arxiv_id"], ref["page_number"], ref.get("page_chunk_index", 0))
            passage = lookup.get(key)
            if passage is None:
                raise ValueError(f"{question['id']}: no passage found for evidence ref {key}")
            supports.append(passage["id"])
            source_papers.append(
                {
                    "arxiv_id": passage["arxiv_id"],
                    "title": passage["title"],
                    "year": passage["year"],
                    "page_number": passage["page_number"],
                }
            )
        question["supporting_passage_ids"] = list(dict.fromkeys(supports))
        question["source_papers"] = list({paper["arxiv_id"]: paper for paper in source_papers}.values())
        resolved.append(question)
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", type=Path)
    parser.add_argument("--passages", type=Path, default=Path("data/processed/domain_passages.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/domain_questions_resolved.jsonl"))
    args = parser.parse_args()
    result = resolve(rows(args.questions), rows(args.passages))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in result), encoding="utf-8")
    print(f"Resolved evidence for {len(result)} questions to {args.output}")


if __name__ == "__main__":
    main()

