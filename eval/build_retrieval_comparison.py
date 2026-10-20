"""Compare two same-track retrieval artifacts without rewriting either artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BEFORE = ROOT / "eval" / "results" / "domain_retrieval_after_debug.json"
DEFAULT_OUTPUT = ROOT / "docs" / "domain-full-graph-retrieval-comparison.md"
COMPARABLE_SETTINGS = (
    "top_k",
    "candidate_k",
    "graph_hops",
    "graph_seed_k",
    "max_graph_nodes",
    "max_graph_chunks",
    "rrf_k",
    "embedding_model",
    "embedding_revision",
    "entity_seed_k",
    "entity_embedding_model",
    "entity_embedding_revision",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(before: dict[str, Any], after: dict[str, Any]) -> None:
    if before.get("track") != "domain" or after.get("track") != "domain":
        raise ValueError("Both artifacts must evaluate the domain track")
    if before.get("question_count") != after.get("question_count"):
        raise ValueError("Question counts differ; a paired comparison is not valid")
    for key in ("questions_sha256", "passages_sha256"):
        if before.get("inputs", {}).get(key) != after.get("inputs", {}).get(key):
            raise ValueError(f"Evaluation inputs differ: {key}")
    for key in COMPARABLE_SETTINGS:
        left = before.get("settings", {}).get(key)
        right = after.get("settings", {}).get(key)
        if left is not None and right is not None and left != right:
            raise ValueError(f"Evaluation settings differ: {key}: {left!r} != {right!r}")
    if set(before.get("retrievers", {})) != set(after.get("retrievers", {})):
        raise ValueError("Retriever variants differ between artifacts")
    for name in before["retrievers"]:
        left = before["retrievers"][name]
        right = after["retrievers"][name]
        left_ids = [str(row["question_id"]) for row in left.get("records", [])]
        right_ids = [str(row["question_id"]) for row in right.get("records", [])]
        if left_ids != right_ids:
            raise ValueError(f"Question IDs or order differ for {name}")


def metric_cell(before: float, after: float) -> str:
    delta = after - before
    return f"{before:.3f} → {after:.3f} ({delta:+.3f})"


def build_report(before_path: Path, after_path: Path, output_path: Path) -> None:
    before, after = load(before_path), load(after_path)
    validate(before, after)
    variants = before["retrievers"]
    hops = sorted(
        {str(hop) for data in (before, after) for item in data["retrievers"].values() for hop in item["by_hop"]},
        key=int,
    )
    headers = ["Variant", *(f"{hop}-hop R@5 (before → after, Δ)" for hop in hops), "Overall R@5 (before → after, Δ)"]
    lines = [
        "# Full-coverage graph retrieval comparison",
        "",
        f"Same {before['question_count']} domain questions and passage corpus; values are supporting-document recall@5.",
        "Each cell shows `before → after (change)`. Positive change is higher recall; it is descriptive, not a significance claim.",
        "",
        f"- Before: `{before_path.name}` ({before.get('node_count', '—')} nodes, {before.get('edge_count', '—')} edges)",
        f"- After: `{after_path.name}` ({after.get('node_count', '—')} nodes, {after.get('edge_count', '—')} edges)",
        f"- Passage count: {before.get('passage_count', '—')} before; {after.get('passage_count', '—')} after",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---", *(["---:"] * (len(headers) - 1))]) + " |",
    ]
    for name in variants:
        row = [name]
        for hop in hops:
            left = variants[name]["by_hop"].get(hop)
            right = after["retrievers"][name]["by_hop"].get(hop)
            if left is None or right is None:
                row.append("—")
            else:
                row.append(metric_cell(float(left["supporting_recall_at_k"]), float(right["supporting_recall_at_k"])))
        row.append(
            metric_cell(
                float(variants[name]["supporting_recall_at_k"]),
                float(after["retrievers"][name]["supporting_recall_at_k"]),
            )
        )
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(
        [
            "",
            "The domain corpus and graph remain provisional pending relevance/rights review and manual extraction/entity-resolution audits.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Comparison report written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_report(args.before, args.after, args.output)


if __name__ == "__main__":
    main()
