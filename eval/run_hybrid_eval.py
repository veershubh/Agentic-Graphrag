"""Compare BM25, local dense retrieval, and reciprocal-rank fusion on MuSiQue."""

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
from retrieval.dense import DenseRetriever
from retrieval.fusion import reciprocal_rank_fusion


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_interval(values: list[float], replicates: int, seed: int) -> list[float]:
    if not values:
        return [0.0, 0.0]
    generator = random.Random(seed)
    means = sorted(sum(generator.choices(values, k=len(values))) / len(values) for _ in range(replicates))
    return [means[int(0.025 * (replicates - 1))], means[int(0.975 * (replicates - 1))]]


def paired_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    differences = [
        right["supporting_recall_at_k"] - left["supporting_recall_at_k"]
        for left, right in zip(baseline["records"], candidate["records"], strict=True)
    ]
    groups: dict[str, list[float]] = defaultdict(list)
    for left, right in zip(baseline["records"], candidate["records"], strict=True):
        groups[str(left["hop_count"])].append(right["supporting_recall_at_k"] - left["supporting_recall_at_k"])
    return {
        "mean_recall_delta": sum(differences) / len(differences) if differences else 0.0,
        "paired_bootstrap_95_ci": bootstrap_interval(differences, replicates, seed),
        "by_hop": {
            hop: {
                "mean_recall_delta": sum(values) / len(values),
                "paired_bootstrap_95_ci": bootstrap_interval(values, replicates, seed + int(hop)),
            }
            for hop, values in sorted(groups.items(), key=lambda item: int(item[0]))
        },
    }


def summarize(
    questions: list[dict[str, Any]],
    passages: list[dict[str, Any]],
    rankings: list[list[tuple[int, float]]],
    top_k: int,
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    groups: dict[str, list[float]] = defaultdict(list)
    records = []
    for question, ranking in zip(questions, rankings, strict=True):
        expected = set(question.get("supporting_paragraph_ids", []))
        retrieved = ranking[:top_k]
        retrieved_ids = [str(passages[index]["id"]) for index, _score in retrieved]
        recall = len(expected.intersection(retrieved_ids)) / len(expected) if expected else 0.0
        hop = str(question["hop_count"])
        groups[hop].append(recall)
        records.append(
            {
                "question_id": question["id"],
                "hop_count": question["hop_count"],
                "support_count": len(expected),
                "supporting_recall_at_k": recall,
                "retrieved": [
                    {"id": str(passages[index]["id"]), "score": float(score)} for index, score in retrieved
                ],
            }
        )
    values = [record["supporting_recall_at_k"] for record in records]
    return {
        "supporting_recall_at_k": sum(values) / len(values) if values else 0.0,
        "bootstrap_95_ci": bootstrap_interval(values, bootstrap_replicates, bootstrap_seed),
        "by_hop": {
            hop: {
                "questions": len(group),
                "supporting_recall_at_k": sum(group) / len(group),
                "bootstrap_95_ci": bootstrap_interval(group, bootstrap_replicates, bootstrap_seed + int(hop)),
            }
            for hop, group in sorted(groups.items(), key=lambda item: int(item[0]))
        },
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("eval/data/public/musique_v1.0_300.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("eval/data/public/musique_v1.0_corpus.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    parser.add_argument("--output", type=Path, default=Path("eval/results/public_hybrid_v0.1.json"))
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    retrieval_config = config["retrieval"]
    dense_config = retrieval_config["dense"]
    questions = read_jsonl(args.questions)
    passages = read_jsonl(args.passages)
    top_k = int(retrieval_config["top_k"])
    candidate_k = int(dense_config.get("candidate_k", 50))
    bootstrap_replicates = int(retrieval_config.get("bootstrap_replicates", 10000))
    bootstrap_seed = int(retrieval_config.get("bootstrap_seed", 20260928))

    bm25 = BM25(passages, k1=float(retrieval_config["bm25"]["k1"]), b=float(retrieval_config["bm25"]["b"]))
    passage_index = {str(document["id"]): index for index, document in enumerate(passages)}
    lexical_rankings = [bm25.search(question["question"], top_k=candidate_k) for question in questions]
    lexical = [[(passage_index[str(result.document["id"])], result.score) for result in row] for row in lexical_rankings]

    cache_path = Path(dense_config["cache_path"])
    if not cache_path.is_absolute():
        cache_path = REPOSITORY_ROOT / cache_path
    dense = DenseRetriever(
        passages,
        model_name=dense_config["model"],
        revision=dense_config["revision"],
        cache_path=cache_path,
        batch_size=int(dense_config.get("batch_size", 64)),
    )
    dense_rankings = dense.search_many(
        [question["question"] for question in questions],
        top_k=candidate_k,
        batch_size=int(dense_config.get("batch_size", 64)),
    )
    hybrid_rankings = [reciprocal_rank_fusion(sparse, vector, rrf_k=int(dense_config.get("rrf_k", 60))) for sparse, vector in zip(lexical, dense_rankings, strict=True)]

    result = {
        "retrievers": {
            "bm25": summarize(questions, passages, lexical, top_k, bootstrap_replicates, bootstrap_seed),
            "dense": summarize(questions, passages, dense_rankings, top_k, bootstrap_replicates, bootstrap_seed),
            "bm25_dense_rrf": summarize(questions, passages, hybrid_rankings, top_k, bootstrap_replicates, bootstrap_seed),
        },
        "settings": {
            "top_k": top_k,
            "candidate_k": candidate_k,
            "rrf_k": int(dense_config.get("rrf_k", 60)),
            "embedding_model": dense_config["model"],
            "embedding_revision": dense_config["revision"],
            "embedding_cache_hit": dense.cache_hit,
            "bootstrap_replicates": bootstrap_replicates,
            "bootstrap_seed": bootstrap_seed,
        },
        "question_count": len(questions),
        "passage_count": len(passages),
        "inputs": {"questions_sha256": sha256(args.questions), "passages_sha256": sha256(args.passages)},
    }
    result["paired_comparisons"] = {
        "dense_minus_bm25": paired_comparison(
            result["retrievers"]["bm25"], result["retrievers"]["dense"], bootstrap_replicates, bootstrap_seed
        ),
        "bm25_dense_rrf_minus_bm25": paired_comparison(
            result["retrievers"]["bm25"], result["retrievers"]["bm25_dense_rrf"], bootstrap_replicates, bootstrap_seed
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Embedding cache {'hit' if dense.cache_hit else 'created'}: {cache_path}")
    print("| Variant | 2-hop recall@5 | 3-hop recall@5 | 4-hop recall@5 | Overall recall@5 |")
    print("|---|---:|---:|---:|---:|")
    for name, metrics in result["retrievers"].items():
        low, high = metrics["bootstrap_95_ci"]
        print(f"{name}: recall@{top_k}={metrics['supporting_recall_at_k']:.3f} [{low:.3f}, {high:.3f}]")
        hop_values = [metrics["by_hop"][hop]["supporting_recall_at_k"] for hop in ("2", "3", "4")]
        print(f"| {name} | " + " | ".join(f"{value:.3f}" for value in hop_values) + f" | {metrics['supporting_recall_at_k']:.3f} |")
        for hop, values in metrics["by_hop"].items():
            low, high = values["bootstrap_95_ci"]
            print(f"  {hop}-hop: {values['supporting_recall_at_k']:.3f} [{low:.3f}, {high:.3f}]")
    print(f"Detailed results: {args.output}")


if __name__ == "__main__":
    main()
