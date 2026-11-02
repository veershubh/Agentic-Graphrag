#!/usr/bin/env python3
"""
Validation test for extraction prompt v3.

Extracts 20 passages NOT in the pilot audit (triple_audit_v1.0.jsonl),
from different papers, to measure prompt improvement without overfitting.

Usage:
    python scripts/validate_prompt_v3.py
    
Outputs:
    - data/processed/prompt_v3_validation_extractions.jsonl (raw LLM responses)
    - data/processed/prompt_v3_validation_audit.jsonl (triples ready for hand-audit)
"""

import argparse
import json
import random
import sys
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

def get_pilot_paper_ids(audit_path: Path) -> set[str]:
    """Extract paper_ids from pilot audit to avoid overlap."""
    if not audit_path.exists():
        return set()
    
    audit_data = load_jsonl(audit_path)
    paper_ids = set()
    for row in audit_data:
        paper_ids.add(row["paper_id"])
    
    return paper_ids

def main():
    parser = argparse.ArgumentParser(description="Validate extraction prompt v3 on fresh passages")
    parser.add_argument(
        "--passages",
        type=Path,
        default=Path("data/processed/domain_passages.jsonl"),
        help="Input passages file"
    )
    parser.add_argument(
        "--pilot-audit",
        type=Path,
        default=Path("data/processed/triple_audit_v1.0.jsonl"),
        help="Pilot audit file to exclude papers from"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Number of passages to sample for validation"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    args = parser.parse_args()

    random.seed(args.seed)

    # Load data
    print(f"Loading passages from {args.passages}")
    passages = load_jsonl(args.passages)
    
    # Exclude papers from pilot audit
    pilot_paper_ids = get_pilot_paper_ids(args.pilot_audit)
    print(f"Excluding {len(pilot_paper_ids)} papers from pilot audit: {sorted(pilot_paper_ids)}")
    
    # Filter passages not in pilot papers (paper_id is directly in passages)
    # Note: passages have "arxiv:XXXXX" format, pilot audit has "XXXXX" format
    eligible_passages = [
        p for p in passages
        if p.get("paper_id", "").replace("arxiv:", "") not in pilot_paper_ids
    ]
    
    print(f"Eligible passages (not in pilot): {len(eligible_passages)}/{len(passages)}")
    
    if len(eligible_passages) < args.sample_size:
        print(f"WARNING: Only {len(eligible_passages)} eligible passages, requested {args.sample_size}")
        sample_size = len(eligible_passages)
    else:
        sample_size = args.sample_size
    
    # Sample passages
    validation_passages = random.sample(eligible_passages, sample_size)
    
    # Group by paper to show diversity
    papers_in_sample = {}
    for p in validation_passages:
        paper_id = p["paper_id"]
        papers_in_sample[paper_id] = papers_in_sample.get(paper_id, 0) + 1
    
    print(f"\nValidation set: {sample_size} passages from {len(papers_in_sample)} papers")
    for paper_id, count in sorted(papers_in_sample.items()):
        print(f"  {paper_id}: {count} passages")
    
    # Save validation passages
    output_path = Path("data/processed/prompt_v3_validation_passages.jsonl")
    save_jsonl(validation_passages, output_path)
    print(f"\nSaved validation passages to {output_path}")
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Run extraction on validation set:")
    print("   python graph/extract_domain_graph.py \\")
    print("       --inventory data/processed/domain_inventory_passages_v1.0.jsonl \\")
    print("       --passages data/processed/prompt_v3_validation_passages.jsonl \\")
    print("       --output data/processed/prompt_v3_validation_cache.jsonl")
    print()
    print("2. Build audit triples:")
    print("   python graph/audit_triples.py \\")
    print("       --extractions data/processed/prompt_v3_validation_cache.jsonl \\")
    print("       --output data/processed/prompt_v3_validation_audit.jsonl \\")
    print("       --sample-size 20")
    print()
    print("3. Hand-audit 20 triples:")
    print("   python scripts/interactive_audit.py \\")
    print("       --audit-file data/processed/prompt_v3_validation_audit.jsonl")
    print()
    print("4. Score validation accuracy:")
    print("   python graph/audit_triples.py \\")
    print("       --score data/processed/prompt_v3_validation_audit.jsonl")
    print()
    print("5. If accuracy >= 75%: Re-run full extraction (188 passages)")
    print("   If accuracy < 75%: Iterate to prompt v4")

if __name__ == "__main__":
    main()
