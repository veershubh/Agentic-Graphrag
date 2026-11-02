# Triple Audit Instructions

## Overview

This audit measures the accuracy of knowledge graph triples extracted from research papers by a local LLM (Qwen3 4B). You will review **50 randomly sampled triples** and determine whether each triple is correctly supported by its source passage.

## Critical Context

- **Graph retrieval severely underperforms BM25** (recall@5: 0.041 vs 0.549)
- **Triple accuracy is currently UNKNOWN** and blocks further improvements
- **59% of candidate triples were rejected** during ontology validation (532 accepted, 772 rejected)
- This audit will determine whether extraction quality is the root cause

## Decision Gate

The results of this audit will determine the next steps:

- **If accuracy < 0.70**: Extraction prompts MUST be improved before scaling to the full corpus (Task 1.4 becomes critical)
- **If accuracy ≥ 0.70**: Can proceed to full extraction after prompt improvements are tested on a smaller sample

## Files

- **Input worksheet**: `triple_audit_worksheet.csv` (for review in Excel/Sheets)
- **Original data**: `triple_audit_v1.0.jsonl` (complete with metadata)
- **Scoring script**: Run after labeling: `python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl`

## Ontology Reference

### Entity Types
- **Paper**: Research papers (e.g., "BLOOM", "TrGLUE")
- **Method**: Techniques, models, approaches (e.g., "BERT", "attention mechanism")
- **Dataset**: Data collections, benchmarks (e.g., "ImageNet", "SQuAD")
- **Metric**: Evaluation measures (e.g., "accuracy", "F1 score", "BLEU")
- **Task**: Problem types (e.g., "sentiment analysis", "question answering")

### Relation Types
- **PROPOSES**: Paper introduces a Method/Dataset
- **EVALUATES_ON**: Paper/Method tested on Dataset/Metric
- **USES**: Entity employs another entity
- **OUTPERFORMS**: Method beats another Method
- **CITES**: Paper references another Paper

## Review Instructions

### For Each Row:

1. **Read the passage text carefully**
   - The full context is provided in the passage_text column

2. **Examine the triple**
   - **Subject**: The entity performing the action
   - **Predicate**: The relationship type
   - **Object**: The entity being acted upon
   - Format: `subject → predicate → object`

3. **Determine if the triple is explicitly supported**
   
   Ask yourself:
   - Does the passage text **explicitly state or clearly imply** this relationship?
   - Are the entity names accurate (allowing for minor variations like "BERT" vs "BERT model")?
   - Is the predicate appropriate for what the passage describes?

4. **Set `reviewer_correct` field**
   - **`true`** or **`yes`**: The triple is accurate and supported by the passage
   - **`false`** or **`no`**: The triple is incorrect, unsupported, or significantly inaccurate

5. **Add `reviewer_notes` for ambiguous cases** (optional but recommended)
   - Explain edge cases
   - Note if the relationship is implied but not explicit
   - Document if entity names are close but not exact matches
   - Flag if the predicate type seems wrong but the entities are correct

## Scoring Criteria

### ✅ CORRECT (true)

- The triple accurately reflects information in the passage
- Entity names match (exact or minor variations acceptable)
- The predicate correctly describes the relationship
- The relationship is explicitly stated or strongly implied

**Examples of acceptable cases:**
- Passage mentions "we propose BERT" → `Paper PROPOSES BERT` ✅
- Passage says "evaluated on ImageNet" → `Method EVALUATES_ON ImageNet` ✅
- Minor name variations: "attention mechanism" vs "attention" ✅

### ❌ INCORRECT (false)

- The relationship is not mentioned in the passage
- Entity names are wrong or refer to different entities
- The predicate type is incorrect for the relationship described
- The triple contradicts the passage
- The information is too vague or ambiguous to support the specific triple

**Examples of errors:**
- Passage mentions paper A but triple claims paper B ❌
- Passage describes general comparison but triple claims OUTPERFORMS ❌
- Passage discusses a related but different relationship ❌
- Entity names are significantly different or refer to wrong things ❌

## Edge Cases

### Implied Relationships
If a relationship is **strongly implied** but not explicitly stated, mark as **true** if:
- The implication is unambiguous
- A domain expert would agree
- No reasonable alternative interpretation exists

Example: "Our model achieves 95% on MNLI" → `Model EVALUATES_ON MNLI` (true, even if "evaluates" isn't said)

### Entity Name Variations
Accept minor variations:
- "BERT model" vs "BERT" ✅
- "ImageNet dataset" vs "ImageNet" ✅
- "F1 score" vs "F1" ✅

Reject significant mismatches:
- "BERT" vs "ALBERT" ❌
- "ImageNet" vs "COCO" ❌

### Predicate Ambiguity
If entities are correct but the predicate seems wrong:
- Mark as **false**
- Note the issue in `reviewer_notes`: "Entities correct but should be USES not PROPOSES"

### Insufficient Context
If the passage is truncated or lacks context to verify:
- Make your best judgment based on what's shown
- Note in `reviewer_notes`: "Passage truncated, limited context"

## Workflow

### 1. Review in Spreadsheet
Open `triple_audit_worksheet.csv` in Excel, Google Sheets, or similar:
- Each row is one triple to review
- Fill `reviewer_correct` column with `true` or `false`
- Add `reviewer_notes` for any unclear cases

### 2. Transfer Labels to JSONL
After completing the CSV review, update the original JSONL file:
```python
import json
import csv

# Read labels from CSV
labels = {}
with open('data/processed/triple_audit_worksheet.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        labels[row['audit_id']] = {
            'correct': row['reviewer_correct'].strip().lower() in ['true', 'yes', 'correct', '1'],
            'notes': row['reviewer_notes']
        }

# Update JSONL
rows = []
with open('data/processed/triple_audit_v1.0.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            row = json.loads(line)
            audit_id = row['audit_id']
            if audit_id in labels:
                row['reviewer_correct'] = labels[audit_id]['correct']
                row['reviewer_notes'] = labels[audit_id]['notes']
            rows.append(row)

# Write updated JSONL
with open('data/processed/triple_audit_v1.0.jsonl', 'w', encoding='utf-8') as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
```

Or use the provided helper script (if created):
```bash
python scripts/transfer_audit_labels.py
```

### 3. Score the Audit
Run the scoring script:
```bash
python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl
```

This will generate `data/processed/triple_audit_summary.json` with:
- Sample size
- Number of correct triples
- Triple accuracy (percentage)
- Wilson 95% confidence interval

### 4. Interpret Results

The summary will show triple accuracy with a 95% confidence interval.

**Example output:**
```json
{
  "sample_size": 50,
  "correct_count": 38,
  "triple_accuracy": 0.76,
  "wilson_95_ci": [0.623, 0.869],
  "note": "This is accuracy on the reviewed random sample; it does not measure entity-resolution quality."
}
```

**Decision criteria:**
- **Accuracy ≥ 0.70**: Extraction quality is acceptable; proceed with prompt improvements and test before full-scale extraction
- **Accuracy < 0.70**: Extraction prompts need significant improvement (Task 1.4 critical); do NOT scale until accuracy improves

## Quality Tips

1. **Be consistent**: Use the same standards across all 50 reviews
2. **Read carefully**: Don't skim; the passages contain complex technical content
3. **When in doubt**: If you're unsure, mark as false and explain in notes
4. **Document ambiguity**: Use reviewer_notes to capture edge cases for later analysis
5. **Check entity types**: Make sure the entity kinds (Paper/Method/Dataset/Metric/Task) make sense
6. **Verify predicates**: The relationship type should match what the passage describes

## Inter-Annotator Agreement (Optional)

If multiple reviewers are labeling:
- Have 10-20% overlap between reviewers
- Calculate Cohen's kappa or Fleiss' kappa
- Discuss and resolve disagreements
- Target agreement > 0.70

## Timeline

- **Review time**: ~2-3 hours for 50 triples (thorough review)
- **Label transfer**: ~5 minutes
- **Scoring**: <1 minute

## Questions?

If you encounter systematic issues (many similar errors, unclear patterns), document them in a separate file for analysis. These patterns will inform prompt improvements in Task 1.4.

## Important Notes

- This audit measures **extraction accuracy**, not entity resolution quality (aliases, duplicates)
- Entity resolution is evaluated separately in Task 1.2
- The 95% confidence interval accounts for sampling uncertainty
- With 50 samples, the CI width is typically ±12-14 percentage points
