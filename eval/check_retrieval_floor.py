"""Fail a CI run when deterministic public BM25 recall falls below set floors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_hop_floor(value: str) -> tuple[str, float]:
    hop, separator, floor = value.partition("=")
    if not separator or not hop.isdigit():
        raise argparse.ArgumentTypeError("Hop floors must use HOP=VALUE, for example 3=0.39")
    try:
        parsed = float(floor)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Hop floor must be numeric") from error
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("Recall floors must be between 0 and 1")
    return hop, parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--overall-min", type=float, default=0.42)
    parser.add_argument("--hop-min", action="append", type=parse_hop_floor, default=[])
    args = parser.parse_args()
    if not 0.0 <= args.overall_min <= 1.0:
        raise SystemExit("Overall recall floor must be between 0 and 1")

    result = json.loads(args.result.read_text(encoding="utf-8"))
    baseline = result.get("retrievers", {}).get("bm25")
    if baseline is None:
        raise SystemExit("Evaluation artifact has no bm25 retriever results")
    failures = []
    overall = float(baseline["supporting_recall_at_k"])
    print(f"BM25 overall recall@k={overall:.3f} (minimum {args.overall_min:.3f})")
    if overall < args.overall_min:
        failures.append(f"overall recall {overall:.3f} < {args.overall_min:.3f}")
    by_hop = baseline.get("by_hop", {})
    for hop, floor in args.hop_min:
        if hop not in by_hop:
            failures.append(f"missing {hop}-hop results")
            continue
        score = float(by_hop[hop]["supporting_recall_at_k"])
        print(f"BM25 {hop}-hop recall@k={score:.3f} (minimum {floor:.3f})")
        if score < floor:
            failures.append(f"{hop}-hop recall {score:.3f} < {floor:.3f}")
    if failures:
        raise SystemExit("Retrieval quality gate failed: " + "; ".join(failures))


if __name__ == "__main__":
    main()
