# Phase 1 Labeling — 10-Minute Quickstart

⏱️ **Total Time:** ~3 hours (2 hours triple audit + 1 hour entity resolution)

## Step 1: Check Your Progress (10 seconds)

```powershell
cd c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag
python scripts/audit_helper.py
```

This shows:
- ✅ Already labeled triples
- ⏸️  Unlabeled triples  
- Progress: X/50 complete

## Step 2: Label Triple Audit (~2 hours)

### Option A: View All Unlabeled Triples

```powershell
python scripts/audit_helper.py --unlabeled-only
```

### Option B: Edit the JSONL File Directly

Open: `data/processed/triple_audit_v1.0.jsonl` in VS Code

For each row, find:
```json
"reviewer_correct": "",
```

Change to:
```json
"reviewer_correct": "true",    // if passage explicitly supports triple
```

or

```json
"reviewer_correct": "false",   // if not explicitly supported
```

**Use Ctrl+F** to search for `"reviewer_correct": ""` to jump between unlabeled rows.

### Labeling Rules (Be Strict!)

| Does the passage... | Label |
|---|---|
| **Explicitly state** the relationship | `"true"` |
| Imply or suggest but doesn't state | `"false"` |
| Mention both entities but no relationship | `"false"` |
| Hallucinate a relationship | `"false"` |
| Wrong entity type (e.g., "F1" as Method instead of Metric) | `"false"` |

**When in doubt → mark `"false"`**

### Check Progress Anytime

```powershell
python scripts/audit_helper.py
```

## Step 3: Score the Audit (1 second)

After labeling all 50:

```powershell
python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl
```

Output:
```json
{
  "sample_size": 50,
  "correct_count": 42,
  "triple_accuracy": 0.84,
  "wilson_95_ci": [0.71, 0.92]
}
```

### Decision Gate

| Accuracy | Action |
|---|---|
| ≥ 85% | ✅ **PASS** — Scale extraction to full corpus |
| 70–84% | ⚠️ **CONDITIONAL** — Improve prompts first |
| < 70% | ❌ **FAIL** — Rework extraction fundamentally |

## Step 4: Label Entity Resolution (~1 hour)

Open: `data/processed/entity_resolution_worksheet.csv` in Excel or Google Sheets

For each of 34 rows:

1. Compare `entity1_name` vs `entity2_name`
2. Check `similarity_score` (higher = likely same)
3. Look at `aliases` for context
4. Set `decision`:
   - `MERGE` if same entity (set `canonical_entity_id` to preferred ID)
   - `KEEP_SEPARATE` if different

### Merge Guidelines

| Situation | Decision | Example |
|---|---|---|
| Same entity, spelling variant | MERGE | "GPT-3" vs "GPT3" |
| Same entity, different version | KEEP_SEPARATE | "BERT" vs "BERT-large" |
| Acronym vs full name | MERGE | "NER" vs "named entity recognition" |
| Different entities, similar name | KEEP_SEPARATE | "F1 score" vs "F1 race" |

**When in doubt → KEEP_SEPARATE**

## Step 5: Apply Entity Resolution (1 second)

### Dry-run first:
```powershell
python graph/apply_entity_resolution.py --dry-run
```

### If it looks correct:
```powershell
python graph/apply_entity_resolution.py
```

Output shows:
- Entities merged
- Nodes removed
- Edges updated

## Step 6: Report Results

After both tasks complete, report:

```
✅ Phase 1 Labeling Complete

Triple Audit:
- Accuracy: 0.84 (95% CI: 0.71–0.92)
- Correct: 42/50
- Decision Gate: PASS

Entity Resolution:
- Reviewed: 34/34 pairs
- Merge: 12 decisions
- Keep Separate: 22 decisions
- Nodes removed: 12 duplicates
```

---

## Keyboard Shortcuts for Labeling

In VS Code editing `triple_audit_v1.0.jsonl`:

- **Ctrl+F** — Find next `"reviewer_correct": ""`
- **Ctrl+H** — Find & Replace
- **Alt+↑/↓** — Move line up/down
- **Ctrl+/** — Toggle comment (for notes)

---

## Common Questions

**Q: Can I do this in multiple sessions?**  
Yes! The JSONL file saves your progress. Run `python scripts/audit_helper.py` anytime to see how many remain.

**Q: What if I'm unsure about a triple?**  
Mark it `"false"` and add a note:
```json
"reviewer_correct": "false",
"reviewer_notes": "Triple implied but not explicitly stated"
```

**Q: Can I edit the CSV for triple audit?**  
⚠️ **NO** — Edit the `.jsonl` file. The scoring script ignores the CSV.

**Q: Do I need to finish triples before entity resolution?**  
No, you can do them in parallel or in any order. But both must be complete before Phase 2.

---

**Ready?** Run:
```powershell
cd c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag
python scripts/audit_helper.py
```
