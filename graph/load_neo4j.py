"""Load consolidated graph files into Neo4j using idempotent batched writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from graph.ontology import PREDICATES


CONSTRAINTS = (
    "CREATE CONSTRAINT graph_entity_id IF NOT EXISTS FOR (n:GraphEntity) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_evidence_id IF NOT EXISTS FOR (n:GraphEvidence) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_source_chunk_id IF NOT EXISTS FOR (n:SourceChunk) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT graph_source_paper_id IF NOT EXISTS FOR (n:SourcePaper) REQUIRE n.id IS UNIQUE",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def batches(rows: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [rows[start : start + batch_size] for start in range(0, len(rows), batch_size)]


def transaction_write(tx: Any, query: str, rows: list[dict[str, Any]]) -> None:
    tx.run(query, rows=rows).consume()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=Path("data/processed/domain_graph_nodes.jsonl"))
    parser.add_argument("--edges", type=Path, default=Path("data/processed/domain_graph_edges.jsonl"))
    parser.add_argument("--database", default=os.environ.get("NEO4J_DATABASE", "neo4j"))
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and report counts without connecting")
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("Batch size must be positive")

    node_rows = read_jsonl(args.nodes)
    edge_rows = read_jsonl(args.edges)
    entity_ids = {str(row["id"]) for row in node_rows}
    if len(entity_ids) != len(node_rows):
        raise SystemExit("Node input contains duplicate entity IDs")
    if any(str(edge[key]) not in entity_ids for edge in edge_rows for key in ("subject_id", "object_id")):
        raise SystemExit("Edge input references an entity ID absent from the node input")
    unsupported = sorted({str(edge["predicate"]) for edge in edge_rows} - set(PREDICATES))
    if unsupported:
        raise SystemExit(f"Unsupported edge predicates: {unsupported}")

    edges_by_predicate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_rows = []
    for edge in edge_rows:
        edges_by_predicate[str(edge["predicate"])].append(edge)
        for evidence in edge.get("evidence", []):
            chunk_id = str(evidence["source_chunk_id"])
            evidence_id = "evidence_" + hashlib.sha256(f"{edge['id']}:{chunk_id}".encode("utf-8")).hexdigest()[:24]
            evidence_rows.append(
                {
                    "id": evidence_id,
                    "edge_id": str(edge["id"]),
                    "predicate": str(edge["predicate"]),
                    "source_chunk_id": chunk_id,
                    "paper_id": str(evidence["paper_id"]),
                    "confidence": float(evidence["confidence"]),
                }
            )

    counts = {
        "nodes": len(node_rows),
        "edges": len(edge_rows),
        "edge_evidence": len(evidence_rows),
        "batches": sum(len(batches(rows, args.batch_size)) for rows in [node_rows, evidence_rows, *edges_by_predicate.values()]),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(counts, indent=2))
        return

    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not username or not password:
        raise SystemExit("Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD before loading")
    try:
        from neo4j import GraphDatabase
    except ImportError as error:
        raise SystemExit('Install the optional database dependency with: python -m pip install -e ".[neo4j]"') from error

    node_query = """
    UNWIND $rows AS row
    MERGE (n:GraphEntity {id: row.id})
    SET n.kind = row.kind, n.name = row.name, n.aliases = row.aliases,
        n.source_chunk_ids = row.source_chunk_ids, n.paper_ids = row.paper_ids
    """
    evidence_query = """
    UNWIND $rows AS row
    MATCH ()-[r {id: row.edge_id}]->()
    MERGE (e:GraphEvidence {id: row.id})
    SET e.confidence = row.confidence, e.paper_id = row.paper_id,
        e.source_chunk_id = row.source_chunk_id
    MERGE (r)-[:HAS_EVIDENCE]->(e)
    MERGE (c:SourceChunk {id: row.source_chunk_id})
    MERGE (e)-[:FROM_CHUNK]->(c)
    MERGE (p:SourcePaper {id: row.paper_id})
    MERGE (e)-[:FROM_PAPER]->(p)
    """

    with GraphDatabase.driver(uri, auth=(username, password)) as driver:
        driver.verify_connectivity()
        with driver.session(database=args.database) as session:
            for constraint in CONSTRAINTS:
                session.run(constraint).consume()
            for batch in batches(node_rows, args.batch_size):
                session.execute_write(transaction_write, node_query, batch)
            for predicate, rows in sorted(edges_by_predicate.items()):
                edge_query = f"""
                UNWIND $rows AS row
                MATCH (s:GraphEntity {{id: row.subject_id}})
                MATCH (o:GraphEntity {{id: row.object_id}})
                MERGE (s)-[r:{predicate} {{id: row.id}}]->(o)
                SET r.predicate = row.predicate
                """
                for batch in batches(rows, args.batch_size):
                    session.execute_write(transaction_write, edge_query, batch)
            for batch in batches(evidence_rows, args.batch_size):
                session.execute_write(transaction_write, evidence_query, batch)

    print(json.dumps({**counts, "database": args.database, "status": "loaded"}, indent=2))


if __name__ == "__main__":
    main()
