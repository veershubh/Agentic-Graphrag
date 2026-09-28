"""Build a metadata-only inventory of screened, locally extractable domain papers."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_inventory(
    references: list[dict[str, Any]],
    extracted: list[dict[str, Any]],
    passages: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    min_score: int,
) -> list[dict[str, Any]]:
    reference_by_id = {str(row["arxiv_id"]): row for row in references}
    extracted_by_id = {str(row["arxiv_id"]): row for row in extracted}
    passage_counts = Counter(str(row["arxiv_id"]) for row in passages)
    required_ids = {
        str(reference["arxiv_id"])
        for question in questions
        if question.get("is_answerable")
        for reference in question.get("supporting_evidence_refs", [])
    }

    missing_references = required_ids - reference_by_id.keys()
    missing_extractions = required_ids - extracted_by_id.keys()
    missing_passages = required_ids - passage_counts.keys()
    if missing_references or missing_extractions or missing_passages:
        raise ValueError(
            "Frozen QA source coverage is incomplete: "
            f"references={sorted(missing_references)}, "
            f"extractions={sorted(missing_extractions)}, "
            f"passages={sorted(missing_passages)}"
        )

    selected = []
    for identifier, paper in extracted_by_id.items():
        reference = reference_by_id.get(identifier)
        if reference is None or int(paper.get("character_count", 0)) <= 0 or passage_counts[identifier] == 0:
            continue
        score = int(reference.get("selection_score", 0))
        required_for_eval = identifier in required_ids
        if score < min_score and not required_for_eval:
            continue
        selected.append(
            {
                "arxiv_id": identifier,
                "title": reference["title"],
                "authors": reference["authors"],
                "year": int(reference["year"]),
                "categories": reference.get("categories", ""),
                "abstract_url": reference["abstract_url"],
                "pdf_url": reference["pdf_url"],
                "selection_score": score,
                "selection_reasons": reference.get("selection_reasons", []),
                "inventory_reason": "frozen_eval_evidence_source" if required_for_eval and score < min_score else "abstract_screen_threshold",
                "pdf_sha256": paper["pdf_sha256"],
                "page_count": int(paper.get("page_count", 0)),
                "character_count": int(paper.get("character_count", 0)),
                "passage_count": passage_counts[identifier],
                "rights_status": paper.get("rights_status", "not_checked; local research use only"),
                "full_text_review_status": "pending_manual_relevance_and_rights_review",
            }
        )
    selected.sort(key=lambda row: (row["year"], row["arxiv_id"]))
    if not 300 <= len(selected) <= 500:
        raise ValueError(f"Inventory must contain 300–500 text-bearing papers; found {len(selected)}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, default=Path("eval/data/domain/papers_candidates.jsonl"))
    parser.add_argument("--papers", type=Path, default=Path("data/processed/domain_papers.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("data/processed/domain_passages.jsonl"))
    parser.add_argument("--questions", type=Path, default=Path("eval/data/domain/questions_v1.0.jsonl"))
    parser.add_argument("--min-selection-score", type=int, default=6)
    parser.add_argument("--output", type=Path, default=Path("eval/data/domain/papers_inventory_v1.0.jsonl"))
    parser.add_argument(
        "--passages-output",
        type=Path,
        default=Path("data/processed/domain_inventory_passages_v1.0.jsonl"),
        help="Write locally filtered passages for the inventory; keep this ignored working data out of Git",
    )
    args = parser.parse_args()

    references = read_jsonl(args.references)
    extracted = read_jsonl(args.papers)
    passages = read_jsonl(args.passages)
    questions = read_jsonl(args.questions)
    inventory = build_inventory(
        references,
        extracted,
        passages,
        questions,
        args.min_selection_score,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in inventory), encoding="utf-8")
    inventory_ids = {row["arxiv_id"] for row in inventory}
    inventory_passages = [row for row in passages if str(row.get("arxiv_id", "")) in inventory_ids]
    args.passages_output.parent.mkdir(parents=True, exist_ok=True)
    args.passages_output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in inventory_passages), encoding="utf-8"
    )
    years = dict(sorted(Counter(row["year"] for row in inventory).items()))
    print(f"Wrote {len(inventory)} paper metadata records to {args.output}")
    print(f"By year: {years}")
    print(f"Total extracted characters: {sum(row['character_count'] for row in inventory):,}")
    print(f"Total page-aware passages: {sum(row['passage_count'] for row in inventory):,}")
    print(f"Wrote {len(inventory_passages)} locally filtered passages to {args.passages_output}")


if __name__ == "__main__":
    main()
