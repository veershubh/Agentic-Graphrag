"""Check whether BM25's top score separates answerable and unanswerable domain probes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_scores(path: Path) -> list[tuple[str, float]]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    records = artifact["retrievers"]["bm25"]["records"]
    scored = []
    for record in records:
        retrieved = record.get("retrieved", [])
        scored.append((str(record["question_id"]), float(retrieved[0]["score"]) if retrieved else 0.0))
    return scored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answerable", type=Path, default=Path("eval/results/domain_inventory_bm25_v0.1.json"))
    parser.add_argument("--unanswerable", type=Path, default=Path("eval/results/domain_unanswerable_bm25_v0.1.json"))
    parser.add_argument("--output", type=Path, default=Path("eval/results/domain_abstention_threshold_v0.1.json"))
    args = parser.parse_args()

    positive = read_scores(args.answerable)
    negative = read_scores(args.unanswerable)
    if not positive or not negative:
        raise SystemExit("Both answerable and unanswerable BM25 result sets must be non-empty")
    positive_values = [score for _identifier, score in positive]
    negative_values = [score for _identifier, score in negative]
    no_false_answer_threshold = max(negative_values) + 1e-9
    candidates = sorted(
        {
            min(positive_values + negative_values) - 1.0,
            *positive_values,
            *negative_values,
            no_false_answer_threshold,
            max(positive_values + negative_values) + 1.0,
        }
    )
    sweep: list[dict[str, Any]] = []
    for threshold in candidates:
        sensitivity = sum(score >= threshold for score in positive_values) / len(positive_values)
        specificity = sum(score < threshold for score in negative_values) / len(negative_values)
        sweep.append(
            {
                "threshold": threshold,
                "answerable_recall": sensitivity,
                "unanswerable_rejection_rate": specificity,
                "balanced_accuracy": (sensitivity + specificity) / 2,
            }
        )
    best = max(sweep, key=lambda row: (row["balanced_accuracy"], row["unanswerable_rejection_rate"], -row["threshold"]))
    no_false_answer = next(row for row in sweep if row["threshold"] == no_false_answer_threshold)
    auc = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in positive_values for n in negative_values) / (
        len(positive_values) * len(negative_values)
    )
    result = {
        "metric": "BM25 top-1 score heuristic; not a calibrated answerability model",
        "answerable_question_count": len(positive),
        "unanswerable_question_count": len(negative),
        "answerable_top_score_mean": sum(positive_values) / len(positive_values),
        "unanswerable_top_score_mean": sum(negative_values) / len(negative_values),
        "answerable_top_score_range": [min(positive_values), max(positive_values)],
        "unanswerable_top_score_range": [min(negative_values), max(negative_values)],
        "rank_auc": auc,
        "best_in_sample_balanced_threshold": best,
        "threshold_rejecting_all_unanswerables": {
            "threshold": no_false_answer_threshold,
            "answerable_recall": no_false_answer["answerable_recall"],
            "unanswerable_rejection_rate": no_false_answer["unanswerable_rejection_rate"],
        },
        "answerable_question_ids": [identifier for identifier, _score in positive],
        "unanswerable_question_ids": [identifier for identifier, _score in negative],
        "note": "Thresholds are measured on the same frozen question sets and are exploratory; do not deploy without independent validation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"answerable_question_ids", "unanswerable_question_ids"}}, indent=2))
    print(f"Detailed results: {args.output}")


if __name__ == "__main__":
    main()
