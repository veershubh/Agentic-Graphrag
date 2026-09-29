"""Evaluate the bounded local agent on a deterministic, hop-stratified question sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from eval.answer_metrics import summarize_metrics, exact_match, token_f1
from eval.run_hybrid_eval import read_jsonl, sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("eval/data/domain/questions_v1.0.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("data/processed/domain_inventory_passages_v1.0.jsonl"))
    parser.add_argument("--nodes", type=Path, default=Path("data/processed/domain_graph_nodes.jsonl"))
    parser.add_argument("--edges", type=Path, default=Path("data/processed/domain_graph_edges.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/domain_agent_eval.json"))
    parser.add_argument("--run-directory", type=Path, default=Path("data/processed/agent_eval_runs"))
    parser.add_argument("--per-hop", type=int, default=1, help="First N answerable questions per hop bucket")
    parser.add_argument("--resume", action="store_true", help="Resume completed questions from the output file")
    args = parser.parse_args()
    if args.per_hop < 1:
        raise SystemExit("--per-hop must be positive")

    all_questions = read_jsonl(args.questions)
    answerable = [question for question in all_questions if question.get("is_answerable", True)]
    selected = []
    for hop in sorted({int(question["hop_count"]) for question in answerable}):
        selected.extend([question for question in answerable if int(question["hop_count"]) == hop][: args.per_hop])
    if not selected:
        raise SystemExit("No answerable questions selected")

    results: list[dict[str, Any]] = []
    if args.resume and args.output.exists():
        results = list(json.loads(args.output.read_text(encoding="utf-8")).get("records", []))
        for result in results:
            result.setdefault("latency_seconds", result.get("total_latency_seconds", 0.0))
            result.pop("run_file", None)
    completed_ids = {str(result["question_id"]) for result in results}
    failed_ids = []
    args.run_directory.mkdir(parents=True, exist_ok=True)

    for question in selected:
        question_id = str(question["id"])
        if question_id in completed_ids:
            continue
        run_path = args.run_directory / f"{question_id}.json"
        command = [
            sys.executable,
            str(REPOSITORY_ROOT / "agent" / "run_agent.py"),
            "--question",
            str(question["question"]),
            "--passages",
            str(args.passages),
            "--nodes",
            str(args.nodes),
            "--edges",
            str(args.edges),
            "--config",
            str(args.config),
            "--output",
            str(run_path),
        ]
        completed = subprocess.run(command, cwd=REPOSITORY_ROOT, check=False)
        if completed.returncode != 0:
            print(f"Agent failed for {question_id} with exit code {completed.returncode}; skipping", flush=True)
            failed_ids.append(question_id)
            continue

        run = json.loads(run_path.read_text(encoding="utf-8"))
        answer = str(run.get("answer", ""))
        golds = list(question.get("gold_answers", []))
        supports = set(question.get("supporting_passage_ids", []))
        citations = set(run.get("citation_ids", []))
        retrieved_ids = [str(item["id"]) for item in run.get("retrieved", [])]
        usage = run.get("usage", {})
        record = {
            "question_id": question_id,
            "hop_count": int(question["hop_count"]),
            "prediction": answer,
            "gold_answers": golds,
            "exact_match": exact_match(answer, golds),
            "token_f1": token_f1(answer, golds),
            "abstained": bool(run.get("abstained", False)),
            "citation_valid": bool(run.get("citation_valid", False)),
            "valid_citation_fraction": 1.0 if run.get("citation_valid", False) else 0.0,
            "gold_citation_precision": len(citations & supports) / len(citations) if citations else 0.0,
            "gold_citation_recall": len(citations & supports) / len(supports) if supports else 0.0,
            "supporting_recall_at_k": len(supports & set(retrieved_ids)) / len(supports) if supports else 0.0,
            "retrieved_ids": retrieved_ids,
            "citation_ids": sorted(citations),
            "step_count": len(run.get("steps", [])),
            "stop_reason": run.get("stop_reason"),
            "total_latency_seconds": float(usage.get("total_latency_seconds", 0.0)),
            "latency_seconds": float(usage.get("total_latency_seconds", 0.0)),
            "planner_latency_seconds": float(usage.get("planner_latency_seconds", 0.0)),
            "tool_latency_seconds": float(usage.get("tool_latency_seconds", 0.0)),
            "answer_latency_seconds": float(usage.get("answer_latency_seconds", 0.0)),
            "input_tokens": int(usage.get("planner_input_tokens", 0)) + int(usage.get("answer_input_tokens", 0)),
            "output_tokens": int(usage.get("planner_output_tokens", 0)) + int(usage.get("answer_output_tokens", 0)),
            "estimated_cost_usd": 0.0,
        }
        results.append(record)
        completed_ids.add(question_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"records": results}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"[{len(results)}/{len(selected)}] {question_id} EM={record['exact_match']:.0f} "
            f"F1={record['token_f1']:.3f} steps={record['step_count']} "
            f"latency={record['total_latency_seconds']:.1f}s",
            flush=True,
        )

    groups: dict[str, list[dict[str, Any]]] = {}
    for record in results:
        groups.setdefault(str(record["hop_count"]), []).append(record)
    summary = {
        "track": "domain",
        "runtime": "local_ollama",
        "models": {"planner": "qwen3:4b-instruct", "answer": "qwen3:8b"},
        "per_hop_sample_size": args.per_hop,
        "requested_question_count": len(selected),
        "failed_question_ids": failed_ids,
        "selection": "first answerable items in each hop bucket, preserving frozen file order",
        "agent_limits": tomllib.loads(args.config.read_text(encoding="utf-8")).get("agent", {}),
        "estimated_model_api_cost_usd": 0.0,
        "overall": summarize_metrics(results, 10000, 20260928),
        "by_hop": {
            hop: summarize_metrics(rows, 10000, 20260928 + int(hop))
            for hop, rows in sorted(groups.items(), key=lambda item: int(item[0]))
        },
        "inputs": {
            "questions_sha256": sha256(args.questions),
            "sampled_questions_sha256": hashlib.sha256(
                "".join(json.dumps(question, ensure_ascii=False) + "\n" for question in selected).encode("utf-8")
            ).hexdigest(),
            "passages_sha256": sha256(args.passages),
            "nodes_sha256": sha256(args.nodes),
            "edges_sha256": sha256(args.edges),
            "config_sha256": sha256(args.config),
        },
        "records": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary["overall"], indent=2))
    print(f"Agent evaluation artifact: {args.output}")


if __name__ == "__main__":
    main()
