"""Build a Markdown report from the checked-in evaluation result artifacts."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"


def read_result(filename: str) -> dict[str, Any]:
    path = RESULTS / filename
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"Missing evaluation artifact: {path}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"Expected a JSON object in {path}")
    return value


def metric(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def interval(value: Any) -> str:
    if not isinstance(value, list) or len(value) != 2:
        return "—"
    return f"{metric(value[0])}–{metric(value[1])}"


def retrieval_rows(result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    if "retrievers" in result:
        retrievers = result["retrievers"]
        hops = sorted(
            {str(hop) for values in retrievers.values() for hop in values.get("by_hop", {})},
            key=int,
        )
        top_k = result.get("settings", {}).get("top_k", 5)
        columns = ["Variant", "Questions", *(f"{hop}-hop" for hop in hops), f"Overall R@{top_k}", "95% CI"]
        rows = []
        for name, values in retrievers.items():
            rows.append(
                [
                    name,
                    str(result.get("question_count", "—")),
                    *(metric(values.get("by_hop", {}).get(hop, {}).get("supporting_recall_at_k")) for hop in hops),
                    metric(values.get("supporting_recall_at_k")),
                    interval(values.get("bootstrap_95_ci")),
                ]
            )
        return columns, rows

    # Legacy public BM25 artifact predates the nested "retrievers" schema.
    hops = sorted(result.get("by_hop", {}), key=int)
    columns = ["Variant", "Questions", *(f"{hop}-hop" for hop in hops), "Overall", "95% CI"]
    rows = [[
        result.get("retriever", "bm25"),
        str(result.get("question_count", "—")),
        *(metric(result["by_hop"][hop].get("supporting_recall_at_k")) for hop in hops),
        metric(result.get("supporting_recall_at_k")),
        interval(result.get("bootstrap_95_ci")),
    ]]
    return columns, rows


def markdown_table(columns: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No result rows available._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] + ["---:"] * (len(columns) - 1)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def answer_rows(result: dict[str, Any], label: str) -> tuple[list[str], list[list[str]]]:
    overall = result.get("overall", {})
    hops = sorted(result.get("by_hop", {}), key=int)
    columns = ["Run", "Questions", *(f"{hop}-hop F1" for hop in hops), "EM", "F1 (95% CI)", "Citation valid", "Mean latency (scope)", "API cost"]
    latency_scope = "end-to-end" if "agent pilot" in label.casefold() else "answer only"
    row = [
        label,
        str(overall.get("question_count", result.get("requested_question_count", "—"))),
        *(metric(result["by_hop"][hop].get("token_f1")) for hop in hops),
        metric(overall.get("exact_match")),
        f"{metric(overall.get('token_f1'))} ({interval(overall.get('token_f1_bootstrap_95_ci'))})",
        metric(overall.get("citation_validity_rate")),
        f"{metric(overall.get('mean_latency_seconds'), 1)}s {latency_scope}",
        f"${metric(result.get('estimated_model_api_cost_usd', overall.get('estimated_cost_usd', 0.0)), 2)}",
    ]
    return columns, [row]


def paired_f1_differences(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[tuple[str, int, float, list[float]]]:
    baseline_records = {str(row["question_id"]): row for row in baseline.get("records", [])}
    candidate_records = {str(row["question_id"]): row for row in candidate.get("records", [])}
    if not baseline_records or baseline_records.keys() != candidate_records.keys():
        raise SystemExit("Paired answer comparison requires the same non-empty question IDs in both runs")
    differences_by_hop: dict[str, list[float]] = {}
    for question_id, baseline_record in baseline_records.items():
        candidate_record = candidate_records[question_id]
        if str(baseline_record["hop_count"]) != str(candidate_record["hop_count"]):
            raise SystemExit(f"Hop-count mismatch for paired question {question_id}")
        hop = str(baseline_record["hop_count"])
        differences_by_hop.setdefault(hop, []).append(
            float(candidate_record["token_f1"]) - float(baseline_record["token_f1"])
        )

    def interval(values: list[float], seed: int) -> list[float]:
        rng = random.Random(seed)
        samples = sorted(
            sum(rng.choices(values, k=len(values))) / len(values)
            for _ in range(10000)
        )
        return [samples[249], samples[9749]]

    output = []
    all_differences = [difference for rows in differences_by_hop.values() for difference in rows]
    output.append(("Overall", len(all_differences), sum(all_differences) / len(all_differences), interval(all_differences, 20261001)))
    for hop, values in sorted(differences_by_hop.items(), key=lambda item: int(item[0])):
        output.append((f"{hop}-hop", len(values), sum(values) / len(values), interval(values, 20261001 + int(hop))))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("eval/results-summary.md"))
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output

    public = read_result("public_hybrid_v0.1.json")
    domain = read_result("domain_graph_dense_entity_seed_v0.1.json")
    domain_dense = read_result("domain_dense_v0.1.json")
    public_legacy_bm25 = read_result("public_bm25_v0.1.json")

    sections = [
        "# Evaluation results summary",
        "",
        "Generated from the versioned JSON artifacts in `eval/results/` by `python eval/build_results_report.py`. Retrieval values are supporting-document recall; answer values are local model outputs. Samples and corpora differ across tracks, so compare variants only within the same table and track.",
        "",
        "## Public benchmark retrieval",
        "",
    ]
    pub_cols, pub_rows = retrieval_rows(public)
    legacy_cols, legacy_rows = retrieval_rows(public_legacy_bm25)
    sections.extend([markdown_table(pub_cols, pub_rows), "", "Public BM25-only artifact (same frozen 300-question track):", "", markdown_table(legacy_cols, legacy_rows), ""])

    sections.extend(["## Domain retrieval diagnostic", ""])
    domain_cols, domain_rows = retrieval_rows(domain)
    dense_cols, dense_rows = retrieval_rows(domain_dense)
    # Reuse the canonical question/corpus run once; add variants absent from the graph artifact.
    existing_names = {row[0] for row in domain_rows}
    domain_rows.extend(row for row in dense_rows if row[0] not in existing_names)
    sections.extend([markdown_table(domain_cols, domain_rows), "", "This provisional domain corpus has not completed relevance/rights review; the graph has not passed manual quality audits.", ""])

    sections.extend(["## Answer generation", ""])
    answer_specs = [
        ("public_answer_qwen3_8b_stratified_v0.1.json", "Public Qwen3 8B, stratified 30"),
        ("domain_answer_qwen3_8b_stratified_v0.1.json", "Domain Qwen3 8B, stratified 30"),
        ("domain_fixed_hybrid_answer_qwen3_8b_v0.1.json", "Domain fixed hybrid Qwen3 8B, stratified 30"),
        ("domain_agent_qwen3_8b_pilot_v0.1.json", "Domain agent pilot, 3 total"),
    ]
    answer_table: list[list[str]] = []
    answer_columns: list[str] | None = None
    for filename, label in answer_specs:
        result = read_result(filename)
        columns, rows = answer_rows(result, label)
        answer_columns = columns
        answer_table.extend(rows)
    sections.extend([markdown_table(answer_columns or [], answer_table), "", "The agent result is a three-question wiring pilot and is not directly comparable as a quality estimate. Faithfulness has not been calibrated against human labels.", ""])

    baseline_answer = read_result("domain_answer_qwen3_8b_stratified_v0.1.json")
    fixed_hybrid_answer = read_result("domain_fixed_hybrid_answer_qwen3_8b_v0.1.json")
    differences = paired_f1_differences(baseline_answer, fixed_hybrid_answer)
    sections.extend(
        [
            "## Paired fixed-hybrid answer difference versus BM25",
            "",
            "Token F1 difference on identical question IDs; positive values favor the fixed hybrid. Confidence intervals use 10,000 paired question-bootstrap resamples.",
            "",
            markdown_table(
                ["Bucket", "Questions", "F1 difference", "95% CI"],
                [[label, str(count), metric(delta), interval(ci)] for label, count, delta, ci in differences],
            ),
            "",
        ]
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
