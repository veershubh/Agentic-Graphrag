"""Prepare a local evidence-backed triple audit and score completed labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def wilson_interval(successes: int, sample_size: int, z: float = 1.959963984540054) -> list[float]:
    if sample_size == 0:
        return [0.0, 0.0]
    proportion = successes / sample_size
    denominator = 1 + z * z / sample_size
    center = (proportion + z * z / (2 * sample_size)) / denominator
    margin = z * ((proportion * (1 - proportion) / sample_size + z * z / (4 * sample_size**2)) ** 0.5) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def prepare_audit(
    edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    passages: list[dict[str, Any]],
    *,
    sample_size: int,
    seed: int,
) -> list[dict[str, Any]]:
    node_by_id = {str(node["id"]): node for node in nodes}
    passage_by_id = {str(passage["id"]): passage for passage in passages}
    claims = []
    for edge in edges:
        subject = node_by_id.get(str(edge["subject_id"]))
        object_entity = node_by_id.get(str(edge["object_id"]))
        if subject is None or object_entity is None:
            raise ValueError(f"Edge {edge.get('id')} has a missing endpoint node")
        for evidence in edge.get("evidence", []):
            chunk_id = str(evidence["source_chunk_id"])
            passage = passage_by_id.get(chunk_id)
            if passage is None:
                raise ValueError(f"No local passage found for evidence chunk {chunk_id}")
            audit_id = "audit_" + hashlib.sha256(f"{edge['id']}:{chunk_id}".encode("utf-8")).hexdigest()[:20]
            claims.append(
                {
                    "audit_id": audit_id,
                    "edge_id": str(edge["id"]),
                    "subject": {"id": str(subject["id"]), "kind": subject["kind"], "name": subject["name"]},
                    "predicate": str(edge["predicate"]),
                    "object": {"id": str(object_entity["id"]), "kind": object_entity["kind"], "name": object_entity["name"]},
                    "paper_id": str(evidence["paper_id"]),
                    "source_chunk_id": chunk_id,
                    "passage_text": str(passage.get("text", "")),
                    "extracted_confidence": float(evidence["confidence"]),
                    "reviewer_correct": "",
                    "reviewer_notes": "",
                }
            )
    claims.sort(key=lambda row: row["audit_id"])
    if sample_size < 1:
        raise ValueError("Sample size must be positive")
    return sorted(random.Random(seed).sample(claims, min(sample_size, len(claims))), key=lambda row: row["audit_id"])


def score_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = []
    for row in rows:
        value = row.get("reviewer_correct")
        if isinstance(value, bool):
            labels.append(value)
        elif isinstance(value, str) and value.strip().casefold() in {"true", "yes", "correct", "1"}:
            labels.append(True)
        elif isinstance(value, str) and value.strip().casefold() in {"false", "no", "incorrect", "0"}:
            labels.append(False)
        else:
            raise ValueError(f"Audit row {row.get('audit_id')} has no valid reviewer_correct label")
    correct = sum(labels)
    return {
        "sample_size": len(labels),
        "correct_count": correct,
        "triple_accuracy": correct / len(labels) if labels else None,
        "wilson_95_ci": wilson_interval(correct, len(labels)),
        "note": "This is accuracy on the reviewed random sample; it does not measure entity-resolution quality.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges", type=Path, default=Path("data/processed/domain_graph_edges.jsonl"))
    parser.add_argument("--nodes", type=Path, default=Path("data/processed/domain_graph_nodes.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("data/processed/domain_inventory_passages_v1.0.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/triple_audit_v1.0.jsonl"))
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260929)
    parser.add_argument("--score", type=Path, help="Score a completed audit JSONL instead of preparing a worksheet")
    parser.add_argument("--summary", type=Path, default=Path("data/processed/triple_audit_summary.json"))
    args = parser.parse_args()

    if args.score:
        summary = score_audit(read_jsonl(args.score))
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    rows = prepare_audit(
        read_jsonl(args.edges),
        read_jsonl(args.nodes),
        read_jsonl(args.passages),
        sample_size=args.sample_size,
        seed=args.seed,
    )
    write_jsonl(args.output, rows)
    print(json.dumps({"audit_rows": len(rows), "seed": args.seed, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
