"""Build a Markdown report from the checked-in evaluation result artifacts."""

from __future__ import annotations

import argparse
import json
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
    columns = ["Run", "Questions", *(f"{hop}-hop F1" for hop in hops), "EM", "F1 (95% CI)", "Citation valid", "Mean latency", "API cost"]
    row = [
        label,
        str(overall.get("question_count", result.get("requested_question_count", "—"))),
        *(metric(result["by_hop"][hop].get("token_f1")) for hop in hops),
        metric(overall.get("exact_match")),
        f"{metric(overall.get('token_f1'))} ({interval(overall.get('token_f1_bootstrap_95_ci'))})",
        metric(overall.get("citation_validity_rate")),
        f"{metric(overall.get('mean_latency_seconds'), 1)}s",
        f"${metric(result.get('estimated_model_api_cost_usd', overall.get('estimated_cost_usd', 0.0)), 2)}",
    ]
    return columns, [row]


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

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
