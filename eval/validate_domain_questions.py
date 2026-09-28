"""Validate domain QA records against locally generated paper passages."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(questions: list[dict[str, Any]], passages: list[dict[str, Any]], require_full_set: bool) -> list[str]:
    errors = []
    ids = [question.get("id") for question in questions]
    if len(ids) != len(set(ids)):
        errors.append("Question IDs are not unique")
    passage_ids = {passage["id"] for passage in passages}
    if not questions:
        errors.append("Question file is empty")
    for question in questions:
        identifier = question.get("id", "<missing-id>")
        if not question.get("question", "").strip():
            errors.append(f"{identifier}: question text is empty")
        if question.get("hop_count") not in (1, 2, 3):
            errors.append(f"{identifier}: hop_count must be 1, 2, or 3")
        support_ids = question.get("supporting_passage_ids", [])
        if question.get("is_answerable"):
            if not question.get("gold_answers"):
                errors.append(f"{identifier}: answerable question has no gold answer")
            missing = set(support_ids) - passage_ids
            if not support_ids or missing:
                errors.append(f"{identifier}: no support or unknown passage IDs {sorted(missing)}")
        elif question.get("gold_answers") or support_ids:
            errors.append(f"{identifier}: unanswerable question must have no gold answer or support passage")
        if question.get("review_status") not in {"pending", "verified", "rejected"}:
            errors.append(f"{identifier}: invalid review_status")
    if require_full_set:
        if not 100 <= len(questions) <= 150:
            errors.append(f"Full domain set must contain 100–150 questions; found {len(questions)}")
        unanswerable = sum(not question.get("is_answerable") for question in questions)
        ratio = unanswerable / len(questions) if questions else 0
        if not 0.10 <= ratio <= 0.15:
            errors.append(f"Unanswerable share must be 10–15%; found {ratio:.1%}")
        hops = Counter(question.get("hop_count") for question in questions)
        if any(hops.get(hop, 0) == 0 for hop in (1, 2, 3)):
            errors.append(f"Full domain set must include each hop count 1, 2, and 3; found {dict(hops)}")
        pending = [question["id"] for question in questions if question.get("review_status") != "verified"]
        if pending:
            errors.append(f"Full domain set has questions without verified author review: {len(pending)}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", type=Path)
    parser.add_argument("--passages", type=Path, default=Path("data/processed/domain_passages.jsonl"))
    parser.add_argument("--require-full-set", action="store_true")
    args = parser.parse_args()
    errors = validate(read_jsonl(args.questions), read_jsonl(args.passages), args.require_full_set)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validated {len(read_jsonl(args.questions))} domain questions against passages")


if __name__ == "__main__":
    main()

