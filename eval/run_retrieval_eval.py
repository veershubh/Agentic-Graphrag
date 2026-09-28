"""Run the retrieval-only public MuSiQue baseline and report evidence recall."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from retrieval.bm25 import BM25


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_interval(values: list[float], replicates: int, seed: int) -> list[float]:
    if not values:
        return [0.0, 0.0]
    generator = random.Random(seed)
    means = sorted(
        sum(generator.choices(values, k=len(values))) / len(values)
        for _ in range(replicates)
    )
    return [means[int(0.025 * (replicates - 1))], means[int(0.975 * (replicates - 1))]]


def evaluate(
    questions: list[dict[str, Any]],
    passages: list[dict[str, Any]],
    top_k: int,
    k1: float,
    b: float,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    retriever = BM25(passages, k1=k1, b=b)
    groups: dict[str, list[float]] = defaultdict(list)
    records = []
    for question in questions:
        results = retriever.search(question["question"], top_k=top_k)
        expected = set(question.get("supporting_paragraph_ids", []))
        retrieved = [str(result.document["id"]) for result in results]
        recall = len(expected.intersection(retrieved)) / len(expected) if expected else 0.0
        hop = str(question["hop_count"])
        groups[hop].append(recall)
        records.append(
            {
                "question_id": question["id"],
                "hop_count": question["hop_count"],
                "support_count": len(expected),
                "supporting_recall_at_k": recall,
                "retrieved": [{"id": result.document["id"], "score": result.score} for result in results],
            }
        )
    by_hop = {
        hop: {
            "questions": len(values),
            "supporting_recall_at_k": sum(values) / len(values) if values else 0.0,
            "bootstrap_95_ci": bootstrap_interval(values, bootstrap_replicates, bootstrap_seed + int(hop)),
        }
        for hop, values in sorted(groups.items(), key=lambda item: int(item[0]))
    }
    all_values = [record["supporting_recall_at_k"] for record in records]
    return {
        "retriever": "BM25 Okapi",
        "top_k": top_k,
        "parameters": {"k1": k1, "b": b},
        "question_count": len(questions),
        "passage_count": len(passages),
        "supporting_recall_at_k": sum(all_values) / len(all_values) if all_values else 0.0,
        "bootstrap_95_ci": bootstrap_interval(all_values, bootstrap_replicates, bootstrap_seed),
        "bootstrap": {"replicates": bootstrap_replicates, "seed": bootstrap_seed, "unit": "question"},
        "by_hop": by_hop,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("eval/data/public/musique_v1.0_300.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("eval/data/public/musique_v1.0_corpus.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/musique_bm25_retrieval.json"))
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    retrieval_config = config["retrieval"]
    bm25_config = retrieval_config.get("bm25", {})
    questions = read_jsonl(args.questions)
    passages = read_jsonl(args.passages)
    result = evaluate(
        questions,
        passages,
        top_k=int(retrieval_config["top_k"]),
        k1=float(bm25_config.get("k1", 1.5)),
        b=float(bm25_config.get("b", 0.75)),
        bootstrap_replicates=int(retrieval_config.get("bootstrap_replicates", 10000)),
        bootstrap_seed=int(retrieval_config.get("bootstrap_seed", 20260928)),
    )
    result["inputs"] = {
        "questions_sha256": sha256(args.questions),
        "passages_sha256": sha256(args.passages),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"BM25 supporting-document recall@{result['top_k']}: {result['supporting_recall_at_k']:.3f}")
    print(f"95% question-bootstrap CI: [{result['bootstrap_95_ci'][0]:.3f}, {result['bootstrap_95_ci'][1]:.3f}]")
    for hop, metrics in result["by_hop"].items():
        low, high = metrics["bootstrap_95_ci"]
        print(f"{hop}-hop: recall@{result['top_k']}={metrics['supporting_recall_at_k']:.3f} [{low:.3f}, {high:.3f}] (n={metrics['questions']})")
    print(f"Detailed retrieval records: {args.output}")


if __name__ == "__main__":
    main()
