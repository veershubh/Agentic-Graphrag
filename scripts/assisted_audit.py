#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assisted triple audit - suggests likely answers to speed up labeling."""

import json
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))


def suggest_label(subject_name: str, predicate: str, object_name: str, passage: str) -> tuple[str, str]:
    """Suggest likely label based on simple heuristics. Returns (suggestion, reason)."""
    
    passage_lower = passage.lower()
    subj_lower = subject_name.lower()
    obj_lower = object_name.lower()
    
    # Check if both entities are mentioned
    subj_in_passage = subj_lower in passage_lower
    obj_in_passage = obj_lower in passage_lower
    
    if not (subj_in_passage and obj_in_passage):
        return ('false', 'One or both entities not in passage')
    
    # Look for explicit relationship patterns
    patterns = {
        'USES': [
            rf'{re.escape(subj_lower)}.*\buses\b.*{re.escape(obj_lower)}',
            rf'{re.escape(subj_lower)}.*\bapplies\b.*{re.escape(obj_lower)}',
            rf'{re.escape(subj_lower)}.*\bemploys\b.*{re.escape(obj_lower)}',
            rf'{re.escape(subj_lower)}.*\butilizes\b.*{re.escape(obj_lower)}',
        ],
        'EVALUATES_ON': [
            rf'{re.escape(subj_lower)}.*\bevaluated? on\b.*{re.escape(obj_lower)}',
            rf'{re.escape(subj_lower)}.*\btested? on\b.*{re.escape(obj_lower)}',
            rf'\beval.*{re.escape(subj_lower)}.*{re.escape(obj_lower)}',
        ],
        'PROPOSES': [
            rf'\bpropose.*{re.escape(obj_lower)}',
            rf'\bintroduce.*{re.escape(obj_lower)}',
            rf'\bpresent.*{re.escape(obj_lower)}',
        ],
        'CITES': [
            rf'\bcites?\b.*{re.escape(obj_lower)}',
            rf'\brefer.*to.*{re.escape(obj_lower)}',
            rf'\[\d+\].*{re.escape(obj_lower)}',
        ],
        'OUTPERFORMS': [
            rf'{re.escape(subj_lower)}.*\boutperforms?\b.*{re.escape(obj_lower)}',
            rf'{re.escape(subj_lower)}.*\bbetter than\b.*{re.escape(obj_lower)}',
            rf'{re.escape(subj_lower)}.*\bsurpasses\b.*{re.escape(obj_lower)}',
        ],
    }
    
    # Check if explicit pattern found
    if predicate in patterns:
        for pattern in patterns[predicate]:
            if re.search(pattern, passage_lower, re.DOTALL):
                return ('true', f'Found explicit pattern for {predicate}')
    
    # Distance-based heuristic: if entities are close together, more likely true
    try:
        subj_pos = passage_lower.index(subj_lower)
        obj_pos = passage_lower.index(obj_lower)
        distance = abs(subj_pos - obj_pos)
        
        if distance < 100:
            return ('uncertain', f'Entities close ({distance} chars) but no explicit pattern')
        else:
            return ('false', f'Entities distant ({distance} chars), likely no relationship')
    except ValueError:
        return ('false', 'Could not find entity positions')


def assisted_audit(audit_path: Path) -> None:
    """Interactive audit with AI-suggested labels."""
    
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
        return
    
    print(f"\n{'='*80}")
    print(f"ASSISTED TRIPLE AUDIT (with AI suggestions)")
    print(f"{'='*80}")
    print(f"\nRemaining: {len(unlabeled_indices)}/50\n")
    print("Instructions:")
    print("  - AI suggests likely answer based on patterns")
    print("  - Press ENTER to accept suggestion")
    print("  - Press 't' or 'f' to override")
    print("  - Press 's' to skip, 'q' to quit")
    print(f"{'='*80}\n")
    
    changes_made = False
    
    for count, idx in enumerate(unlabeled_indices, 1):
        row = rows[idx]
        
        subj_name = row['subject']['name']
        pred = row['predicate']
        obj_name = row['object']['name']
        passage = row['passage_text']
        
        # Get AI suggestion
        suggestion, reason = suggest_label(subj_name, pred, obj_name, passage)
        
        print(f"\n{'='*80}")
        print(f"Triple {count}/{len(unlabeled_indices)}")
        print(f"{'='*80}\n")
        
        print(f"TRIPLE: ({subj_name}) --[{pred}]--> ({obj_name})")
        print(f"\nPASSAGE (first 300 chars):")
        safe_passage = passage[:300].encode('ascii', errors='replace').decode('ascii')
        print(f"{safe_passage}...\n")
        
        print(f"AI SUGGESTION: {suggestion.upper()} - {reason}")
        print("-" * 80)
        
        if suggestion == 'true':
            print("[ENTER] Accept TRUE | [f] Override to FALSE | [s] Skip | [q] Quit")
        elif suggestion == 'false':
            print("[ENTER] Accept FALSE | [t] Override to TRUE | [s] Skip | [q] Quit")
        else:
            print("[t] TRUE | [f] FALSE | [s] Skip | [q] Quit")
        
        print("-" * 80)
        
        while True:
            try:
                choice = input("\nYour choice: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = 'q'
            
            if choice == '':
                # Accept suggestion
                if suggestion in ['true', 'false']:
                    rows[idx]['reviewer_correct'] = suggestion
                    print(f"[LABELED] {suggestion.upper()} (AI suggestion accepted)")
                    changes_made = True
                    break
                else:
                    print("No clear suggestion - please choose t or f")
            elif choice == 't':
                rows[idx]['reviewer_correct'] = 'true'
                print("[LABELED] TRUE")
                changes_made = True
                break
            elif choice == 'f':
                rows[idx]['reviewer_correct'] = 'false'
                print("[LABELED] FALSE")
                changes_made = True
                break
            elif choice == 's':
                print("[SKIPPED]")
                break
            elif choice == 'q':
                if changes_made:
                    save_progress(audit_path, rows)
                print("\n[QUIT] Exiting...")
                return
            else:
                print("Invalid choice")
    
    # Finished all unlabeled
    if changes_made:
        save_progress(audit_path, rows)
    
    remaining = sum(1 for r in rows if r.get('reviewer_correct') == '')
    if remaining == 0:
        print(f"\n{'='*80}")
        print("[COMPLETE] All 50 triples labeled!")
        print(f"{'='*80}\n")
        print("Run: python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl")


def save_progress(audit_path: Path, rows: list) -> None:
    """Save changes."""
    with audit_path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    
    labeled = sum(1 for r in rows if r.get('reviewer_correct') in {'true', 'false'})
    print(f"\n[SAVED] Progress: {labeled}/50 labeled")


if __name__ == '__main__':
    audit_path = REPOSITORY_ROOT / 'data' / 'processed' / 'triple_audit_v1.0.jsonl'
    
    if not audit_path.exists():
        print(f"ERROR: File not found: {audit_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        assisted_audit(audit_path)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED]")
        sys.exit(0)
