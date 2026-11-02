"""Convert entity resolution candidates to human-readable CSV worksheet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from agentic_graphrag.io import read_jsonl


def load_entities_by_id(nodes_path: Path) -> dict[str, dict[str, Any]]:
    """Load all entities indexed by ID."""
    entities = {}
    for node in read_jsonl(nodes_path):
        entities[str(node["id"])] = node
    return entities


def create_worksheet(
    candidates: list[dict[str, Any]],
    entities: dict[str, dict[str, Any]],
    output_path: Path,
) -> None:
    """Convert JSONL candidates to CSV worksheet with context."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8", newline="") as csvfile:
        fieldnames = [
            "pair_id",
            "entity1_id",
            "entity1_name",
            "entity1_type",
            "entity1_aliases",
            "entity1_source_chunks",
            "entity1_papers",
            "entity2_id",
            "entity2_name",
            "entity2_type",
            "entity2_aliases",
            "entity2_source_chunks",
            "entity2_papers",
            "similarity_score",
            "shared_aliases",
            "decision",
            "canonical_entity_id",
            "notes",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for idx, candidate in enumerate(candidates, start=1):
            entity1_id = candidate["entity_id_a"]
            entity2_id = candidate["entity_id_b"]
            
            entity1 = entities.get(entity1_id, {})
            entity2 = entities.get(entity2_id, {})
            
            row = {
                "pair_id": f"pair_{idx:04d}",
                "entity1_id": entity1_id,
                "entity1_name": candidate["name_a"],
                "entity1_type": candidate["kind"],
                "entity1_aliases": "; ".join(entity1.get("aliases", [])),
                "entity1_source_chunks": "; ".join(entity1.get("source_chunk_ids", [])),
                "entity1_papers": "; ".join(entity1.get("paper_ids", [])),
                "entity2_id": entity2_id,
                "entity2_name": candidate["name_b"],
                "entity2_type": candidate["kind"],
                "entity2_aliases": "; ".join(entity2.get("aliases", [])),
                "entity2_source_chunks": "; ".join(entity2.get("source_chunk_ids", [])),
                "entity2_papers": "; ".join(entity2.get("paper_ids", [])),
                "similarity_score": f"{candidate['cosine_similarity']:.4f}",
                "shared_aliases": "; ".join(candidate.get("shared_aliases", [])),
                "decision": candidate.get("decision", "UNREVIEWED"),
                "canonical_entity_id": candidate.get("canonical_entity_id", ""),
                "notes": "",
            }
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("data/processed/entity_resolution_candidates.jsonl"),
        help="Input entity resolution candidates JSONL file",
    )
    parser.add_argument(
        "--nodes",
        type=Path,
        default=Path("data/processed/domain_graph_nodes.jsonl"),
        help="Input graph nodes JSONL file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/entity_resolution_worksheet.csv"),
        help="Output CSV worksheet path",
    )
    args = parser.parse_args()
    
    candidates = read_jsonl(args.candidates)
    entities = load_entities_by_id(args.nodes)
    
    create_worksheet(candidates, entities, args.output)
    
    print(json.dumps({
        "candidate_count": len(candidates),
        "entity_count": len(entities),
        "output": str(args.output),
        "status": "Worksheet created successfully",
    }, indent=2))


if __name__ == "__main__":
    main()
