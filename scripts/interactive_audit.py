#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interactive triple audit labeling - makes the process much faster."""

import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.agentic_graphrag.io import read_jsonl


def interactive_audit(audit_path: Path) -> None:
    """Interactive labeling session with keyboard shortcuts."""
    
    # Load all triples
    with audit_path.open('r', encoding='utf-8') as f:
        lines = f.readlines()
    
    rows = [json.loads(line) for line in lines if line.strip()]
    
    # Find unlabeled
    unlabeled_indices = [
        i for i, row in enumerate(rows)
        if row.get('reviewer_correct') == ''
    ]
    
    if not unlabeled_indices:
        print("\n[COMPLETE] All 50 triples already labeled!")
        print("\nRun: python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl")
        return
    
    print(f"\n{'='*80}")
    print(f"INTERACTIVE TRIPLE AUDIT")
    print(f"{'='*80}")
    print(f"\nLabeled: {50 - len(unlabeled_indices)}/50")
    print(f"Remaining: {len(unlabeled_indices)}\n")
    print("Instructions:")
    print("  - Read the passage and triple")
    print("  - Press 't' if passage EXPLICITLY supports the triple")
    print("  - Press 'f' if NOT explicitly supported")
    print("  - Press 's' to skip this one")
    print("  - Press 'q' to quit and save progress")
    print(f"{'='*80}\n")
    
    changes_made = False
    
    for count, idx in enumerate(unlabeled_indices, 1):
        row = rows[idx]
        
        audit_id = row['audit_id']
        subj_name = row['subject']['name']
        subj_kind = row['subject']['kind']
        pred = row['predicate']
        obj_name = row['object']['name']
        obj_kind = row['object']['kind']
        passage = row['passage_text']
        
        print(f"\n{'='*80}")
        print(f"Triple {count}/{len(unlabeled_indices)} (Row {idx+1}/50)")
        print(f"ID: {audit_id[-12:]}")
        print(f"{'='*80}\n")
        
        print(f"TRIPLE:")
        print(f"  Subject:   {subj_name} [{subj_kind}]")
        print(f"  Predicate: {pred}")
        print(f"  Object:    {obj_name} [{obj_kind}]")
        print(f"\nPASSAGE:")
        # Handle Unicode safely for Windows console
        safe_passage = passage.encode('ascii', errors='replace').decode('ascii')
        print(f"{safe_passage}\n")
        
        print("-" * 80)
        print("Does the passage EXPLICITLY support this triple?")
        print("[t] TRUE - explicitly states it")
        print("[f] FALSE - not explicitly stated")
        print("[s] SKIP - decide later")
        print("[q] QUIT - save and exit")
        print("-" * 80)
        
        while True:
            try:
                choice = input("\nYour choice (t/f/s/q): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = 'q'
            
            if choice == 't':
                rows[idx]['reviewer_correct'] = 'true'
                print("[LABELED] TRUE - passage supports triple")
                changes_made = True
                break
            elif choice == 'f':
                rows[idx]['reviewer_correct'] = 'false'
                print("[LABELED] FALSE - not explicitly supported")
                changes_made = True
                break
            elif choice == 's':
                print("[SKIPPED] Will ask again later")
                break
            elif choice == 'q':
                if changes_made:
                    save_and_report(audit_path, rows, lines)
                print("\n[QUIT] Exiting...")
                return
            else:
                print("Invalid choice. Please press t, f, s, or q.")
    
    # Finished all unlabeled
    if changes_made:
        save_and_report(audit_path, rows, lines)
    
    remaining = sum(1 for r in rows if r.get('reviewer_correct') == '')
    if remaining == 0:
        print(f"\n{'='*80}")
        print("[COMPLETE] All 50 triples labeled!")
        print(f"{'='*80}\n")
        print("Run: python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl")
    else:
        print(f"\n{remaining} triples remaining (you skipped some)")
        print("Run again: python scripts/interactive_audit.py")


def save_and_report(audit_path: Path, rows: list, original_lines: list) -> None:
    """Save changes and show progress."""
    
    # Write updated JSONL
    with audit_path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    
    labeled = sum(1 for r in rows if r.get('reviewer_correct') in {'true', 'false'})
    true_count = sum(1 for r in rows if r.get('reviewer_correct') == 'true')
    false_count = sum(1 for r in rows if r.get('reviewer_correct') == 'false')
    
    print(f"\n{'='*80}")
    print("[SAVED] Progress saved to file")
    print(f"{'='*80}")
    print(f"\nProgress: {labeled}/50 labeled")
    print(f"  TRUE:  {true_count}")
    print(f"  FALSE: {false_count}")
    print(f"  Remaining: {50 - labeled}")
    
    if labeled == 50:
        estimated_accuracy = true_count / 50
        print(f"\nEstimated accuracy: {estimated_accuracy:.2%}")
        print(f"{'='*80}\n")


if __name__ == '__main__':
    audit_path = REPOSITORY_ROOT / 'data' / 'processed' / 'triple_audit_v1.0.jsonl'
    
    if not audit_path.exists():
        print(f"ERROR: File not found: {audit_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        interactive_audit(audit_path)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Exiting...")
        sys.exit(0)
