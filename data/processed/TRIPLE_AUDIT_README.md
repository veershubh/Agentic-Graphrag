# Triple Audit - Quick Start Guide

## 📋 Task Overview

**Goal:** Manually review 50 randomly sampled knowledge graph triples to measure extraction accuracy.

**Time Required:** 2-3 hours for thorough review

**Critical:** Results determine whether to scale extraction to full corpus or improve prompts first.

## 📁 Files

| File | Purpose | Status |
|------|---------|--------|
| `triple_audit_worksheet.csv` | **→ REVIEW THIS FILE** | ⏳ Ready for human labeling |
| `triple_audit_v1.0.jsonl` | Source data with full metadata | ✅ Generated |
| `TRIPLE_AUDIT_INSTRUCTIONS.md` | Detailed labeling guide | ✅ Complete |
| `TRIPLE_AUDIT_DECISION_GATE.md` | Decision criteria and next steps | ✅ Complete |
| `triple_audit_summary.json` | Accuracy results | ⏳ Created after scoring |

## 🚀 Quick Start

### 1. Review Triples (2-3 hours)

Open `triple_audit_worksheet.csv` in Excel or Google Sheets:

```csv
audit_id,subject,predicate,object,passage_text,reviewer_correct,reviewer_notes
audit_xxx,BERT,PROPOSES,attention,"...passage text...",?,?
```

For each row:
- Read the `passage_text`
- Check if `subject → predicate → object` is supported by the text
- Fill `reviewer_correct` with:
  - `true` or `yes` if correct
  - `false` or `no` if incorrect
- Add `reviewer_notes` for ambiguous cases (optional)

**See `TRIPLE_AUDIT_INSTRUCTIONS.md` for detailed criteria.**

### 2. Transfer Labels to JSONL (5 minutes)

After completing CSV review:

```powershell
python scripts/transfer_audit_labels.py
```

This updates `triple_audit_v1.0.jsonl` with your labels.

### 3. Score the Audit (< 1 minute)

```powershell
python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl
```

**Output:** `triple_audit_summary.json`

```json
{
  "sample_size": 50,
  "correct_count": 38,
  "triple_accuracy": 0.76,
  "wilson_95_ci": [0.623, 0.869]
}
```

### 4. Make Decision

**If accuracy ≥ 0.70:**
- ✅ Proceed to entity resolution (Task 1.2)
- ✅ Improve prompts (Task 1.4, optional)
- ✅ Test improvements before scaling

**If accuracy < 0.70:**
- ⚠️ **CRITICAL:** Improve extraction prompts (Task 1.4)
- ⚠️ Do NOT scale until accuracy improves
- ⚠️ Re-audit after improvements

## 📊 What Am I Reviewing?

### Sample Triple
```
Subject: BERT
Predicate: EVALUATES_ON
Object: SQuAD
```

**Question:** Does the passage text explicitly state or strongly imply this relationship?

### Entity Types
- **Paper**: Research papers
- **Method**: Techniques, models
- **Dataset**: Data collections
- **Metric**: Evaluation measures
- **Task**: Problem types

### Relation Types
- **PROPOSES**: Paper introduces Method/Dataset
- **EVALUATES_ON**: Tested on Dataset/Metric
- **USES**: Employs another entity
- **OUTPERFORMS**: Beats another Method
- **CITES**: References another Paper

## ✅ Correct Examples

✅ Passage: "We evaluate BERT on the SQuAD dataset"
- Triple: `BERT → EVALUATES_ON → SQuAD` ✅

✅ Passage: "This paper proposes a novel attention mechanism"
- Triple: `This Paper → PROPOSES → attention mechanism` ✅

## ❌ Incorrect Examples

❌ Passage: "BERT was inspired by transformers"
- Triple: `BERT → USES → transformers` ❌ (not explicit usage)

❌ Passage: "We compare with BERT on SQuAD"
- Triple: `Our Model → OUTPERFORMS → BERT` ❌ (comparison ≠ outperforms)

## 🎯 Decision Gate Summary

| Accuracy Range | Decision | Action |
|---------------|----------|--------|
| ≥ 0.85 | Excellent | Proceed to scaling |
| 0.70-0.84 | Acceptable | Improve prompts, then scale |
| 0.60-0.69 | Below threshold | Must improve prompts |
| < 0.60 | Poor | Reconsider extraction approach |

**Conservative rule:** If the lower bound of 95% CI < 0.65, treat as failing threshold.

## 📝 Tips for Reviewers

1. **Read carefully** - Technical passages require attention
2. **Be consistent** - Use same standards across all 50
3. **When unsure** - Mark as false and document in notes
4. **Minor variations OK** - "BERT model" vs "BERT" is acceptable
5. **Predicate must match** - Correct entities but wrong relation = false

## 🔍 Common Edge Cases

### Implied but not explicit
- "Our model achieves 95% on MNLI" 
- → `Model → EVALUATES_ON → MNLI` ✅ (strongly implied)

### Entity name variations
- "BERT model" = "BERT" ✅
- "BERT" ≠ "ALBERT" ❌

### Truncated passages
- Make best judgment with available text
- Note "limited context" in reviewer_notes

## 📈 Current Extraction Stats

- **Model:** Qwen3 4B (local, Apache 2.0)
- **Passages processed:** 188 (from 19 papers)
- **Entities extracted:** 1,592
- **Triples accepted:** 532
- **Triples rejected:** 772 (59% rejection rate)
- **Audit sample:** 50 random triples

## 🔗 Related Tasks

- **Task 1.2:** Entity resolution (34 candidates, 13 collisions)
- **Task 1.4:** Prompt improvement (triggered if accuracy < 0.70)
- **Task 1.6:** Scale extraction to 325 papers (blocked until audit passes)

## ❓ Questions?

- **Full instructions:** `TRIPLE_AUDIT_INSTRUCTIONS.md`
- **Decision criteria:** `TRIPLE_AUDIT_DECISION_GATE.md`
- **Ontology details:** `graph/ontology.py`
- **Extraction code:** `graph/extract_domain_graph.py`

## 📅 Timeline

| Step | Duration | Status |
|------|----------|--------|
| Generate audit | < 1 min | ✅ Complete |
| Human review | 2-3 hours | ⏳ Pending |
| Transfer labels | 5 min | ⏳ Pending |
| Score audit | < 1 min | ⏳ Pending |
| Make decision | 5 min | ⏳ Pending |

---

**Ready to start?** Open `triple_audit_worksheet.csv` and begin reviewing!
