"""Test entity resolution with sample merge decisions."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from agentic_graphrag.io import read_jsonl


def create_test_worksheet() -> None:
    """Create a test worksheet with 5 sample decisions."""
    worksheet_path = Path("data/processed/entity_resolution_worksheet.csv")
    test_worksheet_path = Path("data/processed/entity_resolution_worksheet_test.csv")
    
    with worksheet_path.open("r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
    
    # Take first 5 rows and create sample decisions
    test_rows = rows[:5]
    
    # Decision 1: Clear merge (politeness judgment singular/plural)
    if len(test_rows) > 0:
        test_rows[0]["decision"] = "MERGE"
        test_rows[0]["canonical_entity_id"] = test_rows[0]["entity1_id"]
        test_rows[0]["notes"] = "Singular/plural variant of same method"
    
    # Decision 2: Keep separate (different model sizes)
    if len(test_rows) > 1:
        test_rows[1]["decision"] = "KEEP_SEPARATE"
        test_rows[1]["canonical_entity_id"] = ""
        test_rows[1]["notes"] = "Different model versions/sizes"
    
    # Decision 3: Merge (high similarity, same context)
    if len(test_rows) > 2:
        test_rows[2]["decision"] = "MERGE"
        test_rows[2]["canonical_entity_id"] = test_rows[2]["entity1_id"]
        test_rows[2]["notes"] = "Same entity, formatting variant"
    
    # Decision 4: Keep separate
    if len(test_rows) > 3:
        test_rows[3]["decision"] = "KEEP_SEPARATE"
        test_rows[3]["canonical_entity_id"] = ""
        test_rows[3]["notes"] = "Different entities despite similarity"
    
    # Decision 5: Uncertain
    if len(test_rows) > 4:
        test_rows[4]["decision"] = "UNCERTAIN"
        test_rows[4]["canonical_entity_id"] = ""
        test_rows[4]["notes"] = "Need domain expert review"
    
    # Write test worksheet
    with test_worksheet_path.open("w", encoding="utf-8", newline="") as outfile:
        fieldnames = list(test_rows[0].keys())
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_rows)
    
    print(json.dumps({
        "test_worksheet": str(test_worksheet_path),
        "sample_size": len(test_rows),
        "merge_count": sum(1 for r in test_rows if r["decision"] == "MERGE"),
        "keep_separate_count": sum(1 for r in test_rows if r["decision"] == "KEEP_SEPARATE"),
        "uncertain_count": sum(1 for r in test_rows if r["decision"] == "UNCERTAIN"),
    }, indent=2))


def verify_resolution_output() -> None:
    """Verify the resolution application produced valid output."""
    nodes_original = read_jsonl(Path("data/processed/domain_graph_nodes.jsonl"))
    nodes_resolved = read_jsonl(Path("data/processed/domain_graph_nodes_resolved_test.jsonl"))
    edges_original = read_jsonl(Path("data/processed/domain_graph_edges.jsonl"))
    edges_resolved = read_jsonl(Path("data/processed/domain_graph_edges_resolved_test.jsonl"))
    
    # Verify node count decreased (due to merges)
    node_reduction = len(nodes_original) - len(nodes_resolved)
    
    # Verify all entity IDs in edges exist in nodes
    resolved_entity_ids = {node["id"] for node in nodes_resolved}
    edge_entity_ids = set()
    for edge in edges_resolved:
        edge_entity_ids.add(edge["subject_id"])
        edge_entity_ids.add(edge["object_id"])
    
    orphaned_ids = edge_entity_ids - resolved_entity_ids
    
    # Verify provenance was preserved
    original_provenance = {
        "source_chunks": set(),
        "papers": set(),
    }
    resolved_provenance = {
        "source_chunks": set(),
        "papers": set(),
    }
    
    for node in nodes_original:
        original_provenance["source_chunks"].update(node.get("source_chunk_ids", []))
        original_provenance["papers"].update(node.get("paper_ids", []))
    
    for node in nodes_resolved:
        resolved_provenance["source_chunks"].update(node.get("source_chunk_ids", []))
        resolved_provenance["papers"].update(node.get("paper_ids", []))
    
    provenance_preserved = (
        original_provenance["source_chunks"] == resolved_provenance["source_chunks"]
        and original_provenance["papers"] == resolved_provenance["papers"]
    )
    
    validation = {
        "original_nodes": len(nodes_original),
        "resolved_nodes": len(nodes_resolved),
        "nodes_removed": node_reduction,
        "original_edges": len(edges_original),
        "resolved_edges": len(edges_resolved),
        "orphaned_entity_references": len(orphaned_ids),
        "provenance_preserved": provenance_preserved,
        "validation_passed": node_reduction > 0 and len(orphaned_ids) == 0 and provenance_preserved,
    }
    
    print(json.dumps(validation, indent=2))
    
    if not validation["validation_passed"]:
        print("\n⚠️  VALIDATION FAILED", file=sys.stderr)
        if len(orphaned_ids) > 0:
            print(f"  - {len(orphaned_ids)} orphaned entity references in edges", file=sys.stderr)
        if not provenance_preserved:
            print("  - Provenance was not fully preserved", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n✓ All validation checks passed")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-test", action="store_true", help="Create test worksheet")
    parser.add_argument("--verify", action="store_true", help="Verify resolution output")
    args = parser.parse_args()
    
    if args.create_test:
        create_test_worksheet()
    elif args.verify:
        verify_resolution_output()
    else:
        print("Use --create-test to generate test data or --verify to check output")


if __name__ == "__main__":
    main()
