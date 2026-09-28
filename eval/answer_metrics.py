"""Answer and citation metrics for generated QA predictions."""

from __future__ import annotations

import string
import random
from collections import Counter
from typing import Any


ARTICLES = {"a", "an", "the"}
PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def normalize_answer(answer: str) -> str:
    text = answer.casefold().translate(PUNCTUATION_TABLE)
    return " ".join(token for token in text.split() if token not in ARTICLES)


def exact_match(prediction: str, gold_answers: list[str]) -> float:
    normalized = normalize_answer(prediction)
    return float(any(normalized == normalize_answer(gold) for gold in gold_answers))


def token_f1(prediction: str, gold_answers: list[str]) -> float:
    predicted_tokens = normalize_answer(prediction).split()
    best = 0.0
    for gold in gold_answers:
        gold_tokens = normalize_answer(gold).split()
        if not predicted_tokens or not gold_tokens:
            score = float(predicted_tokens == gold_tokens)
        else:
            overlap = sum((Counter(predicted_tokens) & Counter(gold_tokens)).values())
            if overlap == 0:
                score = 0.0
            else:
                precision = overlap / len(predicted_tokens)
                recall = overlap / len(gold_tokens)
                score = 2 * precision * recall / (precision + recall)
        best = max(best, score)
    return best


def citation_metrics(cited_ids: list[str], retrieved_ids: list[str], abstained: bool = False) -> dict[str, Any]:
    retrieved = set(retrieved_ids)
    citations = [str(identifier) for identifier in cited_ids]
    valid = [identifier in retrieved for identifier in citations]
    citation_valid = (not citations) if abstained else (bool(citations) and all(valid))
    return {
        "citation_ids": citations,
        "citation_valid": citation_valid,
        "valid_citation_fraction": (sum(valid) / len(valid)) if valid else (1.0 if abstained else 0.0),
        "unsupported_citation_ids": [identifier for identifier, is_valid in zip(citations, valid, strict=True) if not is_valid],
    }


def bootstrap_interval(values: list[float], replicates: int, seed: int) -> list[float]:
    if not values:
        return [0.0, 0.0]
    generator = random.Random(seed)
    means = sorted(sum(generator.choices(values, k=len(values))) / len(values) for _ in range(replicates))
    return [means[int(0.025 * (replicates - 1))], means[int(0.975 * (replicates - 1))]]


def summarize_metrics(records: list[dict[str, Any]], bootstrap_replicates: int, bootstrap_seed: int) -> dict[str, Any]:
    if not records:
        return {"question_count": 0}
    latencies = sorted(record["latency_seconds"] for record in records)
    summary = {
        "question_count": len(records),
        "exact_match": sum(record["exact_match"] for record in records) / len(records),
        "token_f1": sum(record["token_f1"] for record in records) / len(records),
        "citation_validity_rate": sum(record["citation_valid"] for record in records) / len(records),
        "mean_valid_citation_fraction": sum(record["valid_citation_fraction"] for record in records) / len(records),
        "mean_gold_citation_precision": sum(record["gold_citation_precision"] for record in records) / len(records),
        "mean_gold_citation_recall": sum(record["gold_citation_recall"] for record in records) / len(records),
        "supporting_recall_at_k": sum(record["supporting_recall_at_k"] for record in records) / len(records),
        "mean_latency_seconds": sum(record["latency_seconds"] for record in records) / len(records),
        "p50_latency_seconds": latencies[int(0.50 * (len(latencies) - 1))],
        "p95_latency_seconds": latencies[int(0.95 * (len(latencies) - 1))],
        "mean_input_tokens": sum(record["input_tokens"] for record in records) / len(records),
        "mean_output_tokens": sum(record["output_tokens"] for record in records) / len(records),
    }
    costs = [record["estimated_cost_usd"] for record in records]
    summary["estimated_cost_usd"] = sum(costs) if costs and all(cost is not None for cost in costs) else None
    summary["mean_cost_usd"] = summary["estimated_cost_usd"] / len(records) if summary["estimated_cost_usd"] is not None else None
    for index, metric in enumerate((
        "exact_match",
        "token_f1",
        "citation_valid",
        "supporting_recall_at_k",
        "gold_citation_precision",
        "gold_citation_recall",
    )):
        summary[f"{metric}_bootstrap_95_ci"] = bootstrap_interval(
            [float(record[metric]) for record in records], bootstrap_replicates, bootstrap_seed + index
        )
    return summary
