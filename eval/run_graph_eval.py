"""Evaluate lexical- and dense-seeded graph retrieval on the frozen domain track."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from eval.run_hybrid_eval import paired_comparison, read_jsonl, sha256, summarize
from retrieval.bm25 import BM25
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.graph import GraphIndex


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=Path("eval/data/domain/questions_v1.0.jsonl"))
    parser.add_argument("--passages", type=Path, default=Path("data/processed/domain_inventory_passages_v1.0.jsonl"))
    parser.add_argument("--nodes", type=Path, default=Path("data/processed/domain_graph_nodes.jsonl"))
    parser.add_argument("--edges", type=Path, default=Path("data/processed/domain_graph_edges.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    parser.add_argument("--output", type=Path, default=Path("eval/results/domain_graph_v0.1.json"))
    parser.add_argument("--embedding-cache", type=Path, default=Path("data/processed/domain_graph_dense_cache.npz"))
    parser.add_argument(
        "--entity-embedding-cache",
        type=Path,
        default=Path("data/processed/domain_graph_entity_dense_cache.npz"),
        help="Local vector cache for entity names and aliases used to seed graph expansion",
    )
    parser.add_argument(
        "--include-dense",
        action="store_true",
        help="Add local dense passage retrieval and dense entity seeds for graph expansion; can be slow on CPU",
    )
    parser.add_argument("--top-k", type=int, help="Override the configured result cutoff")
    parser.add_argument("--graph-hops", type=int, help="Override graph expansion depth")
    args = parser.parse_args()

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    retrieval_config = config["retrieval"]
    dense_config = retrieval_config["dense"]
    all_questions = read_jsonl(args.questions)
    questions = [question for question in all_questions if question.get("is_answerable", True)]
    if not questions:
        raise SystemExit("No answerable questions in the selected input")
    if not all("supporting_passage_ids" in question for question in questions):
        raise SystemExit("Graph retrieval evaluation expects the frozen domain questions")

    passages = read_jsonl(args.passages)
    nodes = read_jsonl(args.nodes)
    edges = read_jsonl(args.edges)
    top_k = args.top_k if args.top_k is not None else int(retrieval_config["top_k"])
    graph_hops = args.graph_hops if args.graph_hops is not None else int(retrieval_config.get("graph_hops", 2))
    if top_k < 1 or graph_hops < 1:
        raise SystemExit("top-k and graph hops must be positive integers")
    candidate_k = int(dense_config.get("candidate_k", 50))
    graph_seed_k = int(retrieval_config.get("entity_seed_k", 10))
    bootstrap_replicates = int(retrieval_config.get("bootstrap_replicates", 10000))
    bootstrap_seed = int(retrieval_config.get("bootstrap_seed", 20260928))
    rrf_k = int(dense_config.get("rrf_k", 60))
    graph = GraphIndex(
        nodes,
        edges,
        passages,
        entity_k1=float(retrieval_config["bm25"]["k1"]),
        entity_b=float(retrieval_config["bm25"]["b"]),
    )
    bm25 = BM25(passages, k1=float(retrieval_config["bm25"]["k1"]), b=float(retrieval_config["bm25"]["b"]))
    passage_index = {str(passage["id"]): index for index, passage in enumerate(passages)}
    lexical = [
        [(passage_index[str(result.document["id"])], result.score) for result in bm25.search(question["question"], candidate_k)]
        for question in questions
    ]
    graph_rankings = [
        graph.expand(
            question["question"],
            hops=graph_hops,
            max_nodes=int(retrieval_config.get("max_graph_nodes", 100)),
            max_chunks=int(retrieval_config.get("max_graph_chunks", 30)),
            seed_limit=graph_seed_k,
        )
        for question in questions
    ]
    rankings = {
        "bm25": lexical,
        "graph": graph_rankings,
        "bm25_graph_rrf": [
            reciprocal_rank_fusion(sparse, graph_rank, rrf_k=rrf_k)
            for sparse, graph_rank in zip(lexical, graph_rankings, strict=True)
        ],
    }
    settings: dict[str, Any] = {
        "top_k": top_k,
        "candidate_k": candidate_k,
        "graph_hops": graph_hops,
        "graph_seed_k": graph_seed_k,
        "max_graph_nodes": int(retrieval_config.get("max_graph_nodes", 100)),
        "max_graph_chunks": int(retrieval_config.get("max_graph_chunks", 30)),
        "entity_seed_method": "BM25 over entity names and aliases",
        "rrf_k": rrf_k,
        "bootstrap_replicates": bootstrap_replicates,
        "bootstrap_seed": bootstrap_seed,
    }
    if args.include_dense:
        from retrieval.dense import DenseRetriever

        cache_path = args.embedding_cache
        if not cache_path.is_absolute():
            cache_path = REPOSITORY_ROOT / cache_path
        dense = DenseRetriever(
            passages,
            model_name=dense_config["model"],
            revision=dense_config["revision"],
            cache_path=cache_path,
            batch_size=int(dense_config.get("batch_size", 64)),
            cpu_threads=int(dense_config.get("cpu_threads", 4)),
        )
        dense_rankings = dense.search_many(
            [question["question"] for question in questions],
            top_k=candidate_k,
            batch_size=int(dense_config.get("batch_size", 64)),
        )
        entity_cache_path = args.entity_embedding_cache
        if not entity_cache_path.is_absolute():
            entity_cache_path = REPOSITORY_ROOT / entity_cache_path
        entity_dense = DenseRetriever(
            graph.entity_documents,
            model_name=dense_config["model"],
            revision=dense_config["revision"],
            cache_path=entity_cache_path,
            batch_size=int(dense_config.get("batch_size", 64)),
            cpu_threads=int(dense_config.get("cpu_threads", 4)),
            encoder=dense.model,
        )
        entity_seed_k = int(retrieval_config.get("entity_seed_k", 10))
        dense_entity_rankings = entity_dense.search_many(
            [question["question"] for question in questions],
            top_k=entity_seed_k,
            batch_size=int(dense_config.get("batch_size", 64)),
        )
        dense_entity_seeds = [
            [str(graph.entity_documents[index]["id"]) for index, _score in ranking]
            for ranking in dense_entity_rankings
        ]
        dense_seeded_graph_rankings = [
            graph.expand(
                question["question"],
                hops=graph_hops,
                max_nodes=int(retrieval_config.get("max_graph_nodes", 100)),
                max_chunks=int(retrieval_config.get("max_graph_chunks", 30)),
                seed_limit=entity_seed_k,
                seed_entity_ids=seed_ids,
            )
            for question, seed_ids in zip(questions, dense_entity_seeds, strict=True)
        ]
        rankings["dense"] = dense_rankings
        rankings["bm25_dense_rrf"] = [
            reciprocal_rank_fusion(sparse, dense_rank, rrf_k=rrf_k)
            for sparse, dense_rank in zip(lexical, dense_rankings, strict=True)
        ]
        rankings["bm25_dense_graph_rrf"] = [
            reciprocal_rank_fusion(sparse, dense_rank, graph_rank, rrf_k=rrf_k)
            for sparse, dense_rank, graph_rank in zip(lexical, dense_rankings, graph_rankings, strict=True)
        ]
        rankings["dense_entity_graph"] = dense_seeded_graph_rankings
        rankings["bm25_dense_entity_graph_rrf"] = [
            reciprocal_rank_fusion(sparse, dense_rank, graph_rank, rrf_k=rrf_k)
            for sparse, dense_rank, graph_rank in zip(
                lexical, dense_rankings, dense_seeded_graph_rankings, strict=True
            )
        ]
        settings.update(
            {
                "embedding_model": dense_config["model"],
                "embedding_revision": dense_config["revision"],
                "embedding_batch_size": int(dense_config.get("batch_size", 64)),
                "embedding_cpu_threads": int(dense_config.get("cpu_threads", 4)),
                "embedding_cache_hit": dense.cache_hit,
                "embedding_cache_path": str(cache_path),
                "entity_seed_method": "local dense retrieval over entity names and aliases",
                "entity_seed_k": entity_seed_k,
                "entity_embedding_model": dense_config["model"],
                "entity_embedding_revision": dense_config["revision"],
                "entity_embedding_cache_hit": entity_dense.cache_hit,
                "entity_embedding_cache_path": str(entity_cache_path),
            }
        )

    summaries = {
        name: summarize(questions, passages, values, top_k, bootstrap_replicates, bootstrap_seed)
        for name, values in rankings.items()
    }
    result = {
        "track": "domain",
        "retrievers": summaries,
        "settings": settings,
        "question_count": len(questions),
        "unanswerable_question_count_excluded": len(all_questions) - len(questions),
        "passage_count": len(passages),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "inputs": {
            "questions_sha256": sha256(args.questions),
            "passages_sha256": sha256(args.passages),
            "nodes_sha256": sha256(args.nodes),
            "edges_sha256": sha256(args.edges),
        },
        "paired_comparisons": {
            f"{name}_minus_bm25": paired_comparison(
                summaries["bm25"], summaries[name], bootstrap_replicates, bootstrap_seed
            )
            for name in summaries
            if name != "bm25"
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({name: value["supporting_recall_at_k"] for name, value in summaries.items()}, indent=2))
    print(f"Detailed results: {args.output}")


if __name__ == "__main__":
    main()
