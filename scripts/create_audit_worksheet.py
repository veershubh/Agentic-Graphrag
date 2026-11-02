"""Create CSV worksheet from triple audit JSONL for human review."""

import csv
import json
from pathlib import Path

def create_worksheet(input_jsonl: Path, output_csv: Path) -> int:
    """Convert JSONL audit file to CSV worksheet."""
    rows = []
    with open(input_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'audit_id',
            'subject',
            'predicate',
            'object',
            'passage_text',
            'reviewer_correct',
            'reviewer_notes'
        ])
        
        for row in rows:
            subject_name = row['subject']['name']
            object_name = row['object']['name']
            passage_text = row['passage_text']
            
            # Truncate long passages for readability
            if len(passage_text) > 800:
                passage_text = passage_text[:800] + '...'
            
            writer.writerow([
                row['audit_id'],
                subject_name,
                row['predicate'],
                object_name,
                passage_text,
                '',  # reviewer_correct (empty for human to fill)
                ''   # reviewer_notes (empty for human to fill)
            ])
    
    return len(rows)


if __name__ == '__main__':
    input_path = Path('data/processed/triple_audit_v1.0.jsonl')
    output_path = Path('data/processed/triple_audit_worksheet.csv')
    
    count = create_worksheet(input_path, output_path)
    print(f'Created worksheet with {count} rows at {output_path}')
