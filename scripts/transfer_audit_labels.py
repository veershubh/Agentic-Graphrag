"""Transfer audit labels from CSV worksheet back to JSONL file."""

import csv
import json
from pathlib import Path


def transfer_labels(csv_path: Path, jsonl_path: Path) -> dict:
    """Transfer reviewer labels from CSV to JSONL."""
    # Read labels from CSV
    labels = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            correct_value = row['reviewer_correct'].strip().lower()
            labels[row['audit_id']] = {
                'correct': correct_value in ['true', 'yes', 'correct', '1'],
                'notes': row['reviewer_notes'].strip()
            }
    
    # Update JSONL
    rows = []
    labeled_count = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                audit_id = row['audit_id']
                if audit_id in labels and labels[audit_id]['correct'] is not None:
                    row['reviewer_correct'] = labels[audit_id]['correct']
                    row['reviewer_notes'] = labels[audit_id]['notes']
                    labeled_count += 1
                rows.append(row)
    
    # Write updated JSONL
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    
    return {
        'total_rows': len(rows),
        'labeled_count': labeled_count,
        'csv_labels': len(labels)
    }


if __name__ == '__main__':
    csv_path = Path('data/processed/triple_audit_worksheet.csv')
    jsonl_path = Path('data/processed/triple_audit_v1.0.jsonl')
    
    stats = transfer_labels(csv_path, jsonl_path)
    print(f"Transferred {stats['labeled_count']}/{stats['total_rows']} labels from CSV to JSONL")
    print(f"CSV contained {stats['csv_labels']} label entries")
