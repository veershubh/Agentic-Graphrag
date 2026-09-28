"""Merge cached chunk extractions into graph nodes, edges, and a safe alias table."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from graph.ontology import ENTITY_KINDS, normalize_name


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def consolidate(extractions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    aliases_to_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in extractions:
        chunk_id = str(row["chunk_id"])
        paper_id = str(row["paper_id"])
        for entity in row.get("entities", []):
            identifier = str(entity["id"])
            kind = str(entity["kind"])
            if kind not in ENTITY_KINDS:
                raise ValueError(f"Unsupported entity kind {kind!r} in chunk {chunk_id}")
            node = nodes.get(identifier)
            if node is None:
                node = {
                    "id": identifier,
                    "kind": kind,
                    "name": str(entity["name"]),
                    "aliases": set(),
                    "source_chunk_ids": set(),
                    "paper_ids": set(),
                }
                nodes[identifier] = node
            elif node["kind"] != kind:
                raise ValueError(f"Entity ID {identifier} has conflicting kinds")
            node["aliases"].update(str(alias).strip() for alias in entity.get("aliases", []) if str(alias).strip())
            node["source_chunk_ids"].update(str(value) for value in entity.get("source_chunk_ids", [chunk_id]))
            node["paper_ids"].update(str(value) for value in entity.get("paper_ids", [paper_id]))
            for alias in [node["name"], *node["aliases"]]:
                normalized = normalize_name(alias)
                if normalized:
                    aliases_to_ids[(kind, normalized)].add(identifier)

        for triple in row.get("triples", []):
            subject = str(triple["subject_id"])
            predicate = str(triple["predicate"])
            object_id = str(triple["object_id"])
            key = (subject, predicate, object_id)
            edge = edges.setdefault(
                key,
                {
                    "id": "edge_" + hashlib.sha256("\n".join(key).encode("utf-8")).hexdigest()[:20],
                    "subject_id": subject,
                    "predicate": predicate,
                    "object_id": object_id,
                    "evidence": {},
                },
            )
            evidence_id = str(triple.get("source_chunk_id", chunk_id))
            edge["evidence"][evidence_id] = {
                "source_chunk_id": evidence_id,
                "paper_id": str(triple.get("paper_id", paper_id)),
                "confidence": float(triple["confidence"]),
            }

    missing = sorted(
        {
            endpoint
            for edge in edges.values()
            for endpoint in (edge["subject_id"], edge["object_id"])
            if endpoint not in nodes
        }
    )
    if missing:
        raise ValueError(f"Graph edges reference unknown node IDs: {missing[:5]}")

    node_rows = [
        {
            **node,
            "aliases": sorted(node["aliases"]),
            "source_chunk_ids": sorted(node["source_chunk_ids"]),
            "paper_ids": sorted(node["paper_ids"]),
        }
        for node in sorted(nodes.values(), key=lambda item: item["id"])
    ]
    edge_rows = [
        {**edge, "evidence": sorted(edge["evidence"].values(), key=lambda item: item["source_chunk_id"])}
        for edge in sorted(edges.values(), key=lambda item: item["id"])
    ]
    alias_rows = []
    collisions = []
    for (kind, normalized), identifiers in sorted(aliases_to_ids.items()):
        sorted_ids = sorted(identifiers)
        if len(sorted_ids) == 1:
            alias_rows.append({"kind": kind, "normalized_alias": normalized, "entity_id": sorted_ids[0]})
        else:
            collisions.append({"kind": kind, "normalized_alias": normalized, "candidate_entity_ids": sorted_ids})
    return node_rows, edge_rows, alias_rows, collisions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/domain_graph_pilot.jsonl"))
    parser.add_argument("--nodes", type=Path, default=Path("data/processed/domain_graph_nodes.jsonl"))
    parser.add_argument("--edges", type=Path, default=Path("data/processed/domain_graph_edges.jsonl"))
    parser.add_argument("--aliases", type=Path, default=Path("data/processed/domain_graph_aliases.jsonl"))
    parser.add_argument("--collisions", type=Path, default=Path("data/processed/domain_graph_alias_collisions.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("data/processed/domain_graph_merge_summary.json"))
    args = parser.parse_args()

    extraction_rows = read_jsonl(args.input)
    node_rows, edge_rows, alias_rows, collisions = consolidate(extraction_rows)
    write_jsonl(args.nodes, node_rows)
    write_jsonl(args.edges, edge_rows)
    write_jsonl(args.aliases, alias_rows)
    write_jsonl(args.collisions, collisions)
    summary = {
        "input_extraction_rows": len(extraction_rows),
        "node_count": len(node_rows),
        "edge_count": len(edge_rows),
        "edge_evidence_count": sum(len(edge["evidence"]) for edge in edge_rows),
        "alias_count": len(alias_rows),
        "ambiguous_alias_count": len(collisions),
        "entity_kinds": dict(Counter(node["kind"] for node in node_rows)),
        "predicates": dict(Counter(edge["predicate"] for edge in edge_rows)),
        "outputs": {
            "nodes": str(args.nodes),
            "edges": str(args.edges),
            "aliases": str(args.aliases),
            "ambiguous_aliases": str(args.collisions),
        },
        "note": "Identical normalized names are merged by stable ID; ambiguous aliases remain unresolved for adjudication.",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
