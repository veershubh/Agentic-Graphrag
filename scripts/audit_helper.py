#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interactive helper for triple audit labeling."""

import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.agentic_graphrag.io import read_jsonl


def print_triple_review(audit_path: Path) -> None:
    """Print human-readable triple review sheet."""
    rows = read_jsonl(audit_path)
    
    print(f"\n{'='*80}")
    print(f"TRIPLE AUDIT REVIEW SHEET — {len(rows)} triples to label")
    print(f"File: {audit_path}")
    print(f"{'='*80}\n")
    
    labeled = sum(1 for r in rows if r.get('reviewer_correct') in {'true', 'false'})
    
    print(f"Progress: {labeled}/{len(rows)} labeled\n")
    
    for i, row in enumerate(rows, 1):
        audit_id = row['audit_id']
        subj_name = row['subject']['name']
        subj_kind = row['subject']['kind']
        pred = row['predicate']
        obj_name = row['object']['name']
        obj_kind = row['object']['kind']
        passage = row['passage_text']
        reviewer_correct = row.get('reviewer_correct', '')
        reviewer_notes = row.get('reviewer_notes', '')
        
        status = '[PASS]' if reviewer_correct == 'true' else '[FAIL]' if reviewer_correct == 'false' else '[ ?? ]'
        
        print(f"{status} Row {i:2d}/50 [{audit_id[-12:]}]")
        print(f"  TRIPLE: ({subj_name} [{subj_kind}]) --[{pred}]--> ({obj_name} [{obj_kind}])")
        print(f"  PASSAGE: {passage[:200]}...")
        
        if reviewer_correct:
            print(f"  LABELED: {reviewer_correct}")
            if reviewer_notes:
                print(f"  NOTES: {reviewer_notes}")
        else:
            print(f"  LABELED: [NEEDS REVIEW]")
        
        print()
    
    print(f"\n{'='*80}")
    print(f"Progress: {labeled}/{len(rows)} labeled")
    if labeled < len(rows):
        print(f"Remaining: {len(rows) - labeled}")
        print(f"\nEdit: {audit_path}")
        print(f"Find: \\\"reviewer_correct\\\": \\\"\\\"")
        print(f"Replace with: \\\"reviewer_correct\\\": \\\"true\\\" or \\\"reviewer_correct\\\": \\\"false\\\"")
    else:
        print(f"\n[DONE] All {len(rows)} triples labeled!")
        print(f"\nRun: python graph/audit_triples.py --score {audit_path}")
    print(f"{'='*80}\n")


def print_unlabeled_only(audit_path: Path) -> None:
    """Print only unlabeled triples for focused review."""
    rows = read_jsonl(audit_path)
    unlabeled = [r for r in rows if r.get('reviewer_correct') == '']
    
    if not unlabeled:
        print("[DONE] All triples labeled!")
        return
    
    print(f"\n{'='*80}")
    print(f"UNLABELED TRIPLES — {len(unlabeled)} remaining")
    print(f"{'='*80}\n")
    
    for i, row in enumerate(unlabeled, 1):
        audit_id = row['audit_id']
        subj_name = row['subject']['name']
        pred = row['predicate']
        obj_name = row['object']['name']
        passage = row['passage_text']
        
        print(f"[ ?? ] {i}/{len(unlabeled)} [{audit_id[-12:]}]")
        print(f"  TRIPLE: ({subj_name}) --[{pred}]--> ({obj_name})")
        print(f"  PASSAGE: {passage[:300]}...")
        print(f"  -> Does this passage EXPLICITLY support the triple?")
        print(f"  -> Edit JSONL and set reviewer_correct to true or false")
        print()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--audit',
        type=Path,
        default=REPOSITORY_ROOT / 'data' / 'processed' / 'triple_audit_v1.0.jsonl',
        help='Path to triple audit JSONL file',
    )
    parser.add_argument(
        '--unlabeled-only',
        action='store_true',
        help='Show only unlabeled triples',
    )
    args = parser.parse_args()
    
    if not args.audit.exists():
        print(f"❌ File not found: {args.audit}", file=sys.stderr)
        sys.exit(1)
    
    if args.unlabeled_only:
        print_unlabeled_only(args.audit)
    else:
        print_triple_review(args.audit)
