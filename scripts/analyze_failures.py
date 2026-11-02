#!/usr/bin/env python3
"""Analyze false triple patterns from audit."""

import json
import sys
from pathlib import Path
from collections import Counter

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

audit_path = REPOSITORY_ROOT / 'data' / 'processed' / 'triple_audit_v1.0.jsonl'

with audit_path.open('r', encoding='utf-8') as f:
    rows = [json.loads(l) for l in f if l.strip()]

false_triples = [r for r in rows if r.get('reviewer_correct') == 'false']

print(f'FAILURE ANALYSIS ({len(false_triples)}/50 incorrect)')
print('='*60)

# By predicate
predicates = Counter(r['predicate'] for r in false_triples)
print('\nBy predicate:')
for pred, count in predicates.most_common():
    pct = count / len(false_triples) * 100
    print(f'  {pred:15s} {count:2d} ({pct:4.1f}%)')

# By entity type
print('\nBy subject type:')
subj_types = Counter(r['subject']['kind'] for r in false_triples)
for typ, count in subj_types.most_common():
    print(f'  {typ:10s} {count:2d}')

print('\nBy object type:')
obj_types = Counter(r['object']['kind'] for r in false_triples)
for typ, count in obj_types.most_common():
    print(f'  {typ:10s} {count:2d}')

print('\n' + '='*60)
print('SAMPLE FAILURES (first 5):')
print('='*60)
for i, r in enumerate(false_triples[:5], 1):
    subj = r['subject']['name']
    obj = r['object']['name']
    pred = r['predicate']
    subj_kind = r['subject']['kind']
    obj_kind = r['object']['kind']
    passage = r['passage_text'][:200].encode('ascii', errors='replace').decode('ascii')
    
    print(f"\n{i}. TRIPLE: ({subj}) --[{pred}]--> ({obj})")
    print(f"   TYPES: {subj_kind} -> {obj_kind}")
    print(f"   PASSAGE: {passage}...")
