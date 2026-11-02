#!/usr/bin/env python3
"""
Build audit triples directly from extraction cache for validation.

Simpler than the full pipeline (extract → merge → resolve → audit).
Just samples triples directly from the extraction cache.

Usage:
    python scripts/build_validation_audit.py \\
        --cache data/processed/prompt_v3_validation_cache.jsonl \\
        --passages data/processed/prompt_v3_validation_passages.jsonl \\
        --output data/processed/prompt_v3_validation_audit.jsonl \\
        --sample-size 19
"""

import argparse
import json
import random
from pathlib import Path

def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def save_jsonl(data: list[dict], path: Path) -> None:
    """Save list of dicts to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="Extraction cache JSONL")
    parser.add_argument("--passages", type=Path, required=True, help="Original passages JSONL")
    parser.add_argument("--output", type=Path, required=True, help="Output audit JSONL")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of triples to sample")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    # Load data
    cache_rows = load_jsonl(args.cache)
    passages = load_jsonl(args.passages)
    passages_by_id = {p["id"]: p for p in passages}

    # Collect all triples with passage text
    all_triples = []
    for row in cache_rows:
        chunk_id = row["chunk_id"]
        passage = passages_by_id.get(chunk_id)
        if not passage:
            print(f"WARNING: No passage found for chunk {chunk_id}")
            continue

        # Build entity lookup
        entities_by_id = {e["id"]: e for e in row["entities"]}

        for triple in row["triples"]:
            subject_entity = entities_by_id.get(triple["subject_id"], {})
            object_entity = entities_by_id.get(triple["object_id"], {})

            all_triples.append({
                "paper_id": row["paper_id"],
                "paper_title": passage["title"],
                "chunk_id": chunk_id,
                "passage_text": passage["text"],
                "subject": subject_entity.get("name", "UNKNOWN"),
                "subject_kind": subject_entity.get("kind", "UNKNOWN"),
                "predicate": triple["predicate"],
                "object": object_entity.get("name", "UNKNOWN"),
                "object_kind": object_entity.get("kind", "UNKNOWN"),
                "confidence": triple["confidence"],
                "label": None,  # To be filled by human auditor
                "note": "",  # Optional human note
            })

    print(f"Collected {len(all_triples)} triples from {len(cache_rows)} passages")

    # Sample triples
    if len(all_triples) < args.sample_size:
        print(f"WARNING: Only {len(all_triples)} triples available, sampling all")
        sampled = all_triples
    else:
        sampled = random.sample(all_triples, args.sample_size)

    # Save audit file
    save_jsonl(sampled, args.output)
    print(f"Saved {len(sampled)} triples to {args.output}")

    # Show predicate distribution
    from collections import Counter
    predicate_counts = Counter(t["predicate"] for t in sampled)
    print("\nPredicate distribution in validation audit:")
    for predicate, count in predicate_counts.most_common():
        print(f"  {predicate}: {count}")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print(f"1. Hand-audit {len(sampled)} triples:")
    print(f"   python scripts/interactive_audit.py --audit-file {args.output}")
    print()
    print("2. Score validation accuracy:")
    print(f"   python graph/audit_triples.py --score {args.output}")

if __name__ == "__main__":
    main()
