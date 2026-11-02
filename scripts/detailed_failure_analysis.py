#!/usr/bin/env python3
"""Detailed analysis of all extraction failures with categorization."""

import json
import sys
from pathlib import Path
from collections import Counter

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

audit_path = REPOSITORY_ROOT / 'data' / 'processed' / 'triple_audit_v1.0.jsonl'

with audit_path.open('r', encoding='utf-8') as f:
    rows = [json.loads(l) for l in f if l.strip()]

false_triples = [r for r in rows if r.get('reviewer_correct') == 'false']

print(f'DETAILED FAILURE ANALYSIS')
print('='*80)
print(f'Total failures: {len(false_triples)}/50 (66% accuracy)\n')

# Categorize each failure
categories = {
    'wrong_entity_type': [],
    'implicit_not_explicit': [],
    'hallucinated': [],
    'wrong_predicate': [],
    'other': []
}

print('ALL 17 FAILURES:\n')
print('='*80)

for i, r in enumerate(false_triples, 1):
    subj = r['subject']['name']
    obj = r['object']['name']
    pred = r['predicate']
    subj_kind = r['subject']['kind']
    obj_kind = r['object']['kind']
    passage = r['passage_text']
    audit_id = r['audit_id']
    
    print(f"\n{i}. [{audit_id[-8:]}]")
    print(f"   TRIPLE: ({subj} [{subj_kind}]) --[{pred}]--> ({obj} [{obj_kind}])")
    
    # Analyze passage
    passage_lower = passage.lower()
    subj_in = subj.lower() in passage_lower
    obj_in = obj.lower() in passage_lower
    
    print(f"   In passage: subject={subj_in}, object={obj_in}")
    
    # Show passage context
    safe_passage = passage[:250].encode('ascii', errors='replace').decode('ascii')
    print(f"   PASSAGE: {safe_passage}...")
    print()

print('\n' + '='*80)
print('DIAGNOSTIC SUMMARY')
print('='*80)

# Predicate distribution
print('\nPredicate distribution in failures:')
predicates = Counter(r['predicate'] for r in false_triples)
for pred, count in predicates.most_common():
    total_pred = sum(1 for r in rows if r['predicate'] == pred)
    fail_rate = count / total_pred * 100 if total_pred > 0 else 0
    print(f'  {pred:15s}: {count:2d}/{total_pred:2d} failed ({fail_rate:5.1f}%)')

# Entity type pairs
print('\nEntity type pairs in failures:')
type_pairs = Counter(
    f"{r['subject']['kind']} -> {r['object']['kind']}"
    for r in false_triples
)
for pair, count in type_pairs.most_common(10):
    print(f'  {pair:25s}: {count:2d}')

# Paper as subject
paper_subjects = sum(1 for r in false_triples if r['subject']['kind'] == 'Paper')
print(f'\nPaper as subject: {paper_subjects}/17 ({paper_subjects/17*100:.1f}%)')
print('  ^ This suggests confusion between Paper names and Method/Benchmark names')
