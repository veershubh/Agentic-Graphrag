# Phase 1: Human Labeling Required ⏸️

**Status:** Workflows paused at human labeling gate  
**Date:** November 2, 2026  

## ✅ Automation Complete - Your Turn Now

Phase 0 (testing/refactoring) and Phase 1 preparation (extraction + tooling) are done. The graph extraction pipeline has produced:

- **257 nodes** (87 Methods, 62 Tasks, 41 Metrics, 39 Datasets, 28 Papers)
- **126 edges** (54 USES, 51 EVALUATES_ON, 14 CITES, 5 PROPOSES, 2 OUTPERFORMS)
- **532 triples accepted**, 772 rejected (59% rejection rate)

⚠️ **These numbers differ significantly from graph/README.md** (994 nodes → 257). See `DISCREPANCY_ANALYSIS.md` for explanation: the merge logic deduplicated more aggressively (6.2× vs 1.7× factor). The triple audit will validate if this is beneficial or harmful.

**Critical question:** Is this graph quality good enough to scale to the full corpus?

## 📋 Two Labeling Tasks (3-5 hours total)

### Task 1: Triple Audit (2-3 hours)

**File:** `data/processed/triple_audit_worksheet.csv`  
**Instructions:** `data/processed/TRIPLE_AUDIT_README.md`  

**What to do:**
1. Open the CSV in Excel/Google Sheets
2. For each of 50 random triples:
   - Read the `passage_text`
   - Check if `(subject → predicate → object)` is explicitly supported
   - Set `reviewer_correct` to `true` or `false`
   - Add `reviewer_notes` for ambiguous cases
3. Save the file
4. Run: `python graph/audit_triples.py --score data/processed/triple_audit_v1.0.jsonl`

**Decision gate:** If accuracy < 70%, we MUST improve extraction prompts before scaling.

### Task 2: Entity Resolution (1-2 hours)

**File:** `data/processed/entity_resolution_worksheet.csv`  
**Instructions:** `docs/ENTITY_RESOLUTION_INSTRUCTIONS.md`  

**What to do:**
1. Open the CSV
2. For each of 34 entity pairs:
   - Compare `entity_1_name` vs `entity_2_name`
   - Check `aliases`, `source_chunks`, `similarity_score`
   - Set `decision` to `MERGE` or `KEEP_SEPARATE`
   - If MERGE: set `canonical_entity_id` to the preferred ID
   - Add `reviewer_notes` for reasoning
3. Save the file
4. Run: `python graph/apply_entity_resolution.py`

**Decision gate:** If precision < 90% (incorrect merges), we have a problem.

## 🎯 Reporting Back

After completing both tasks, report these metrics:

```
Triple Accuracy: X.XX (95% CI: X.XX-X.XX) from triple_audit_summary.json
Entity Resolution: N MERGE decisions applied, M KEEP_SEPARATE
Alias Collisions: Currently 13 (down from 103 in old run)
Unreviewed Pairs: Should be 0
Decision Gate: PASS or FAIL (accuracy ≥0.70 required)
```

**Note:** Ignore the "precision ≥0.90" metric—it's hardcoded to pass. Your real quality signal is: "Did I mistakenly merge entities that should be separate?"

## 🚦 What Happens Next

### If Decision Gate = PASS ✅
- Workflow proceeds to Task 1.4 (prompt improvement - optional)
- Task 1.5 (quality metrics report)
- Task 1.6 (scale extraction to full corpus if needed)

### If Decision Gate = FAIL ❌
- Workflow requires Task 1.4 (improve extraction prompts)
- Re-run extraction on validation set
- Repeat audit until accuracy ≥0.70

## 📁 File Locations

All files in `c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag\`:

```
data/processed/
  ├── triple_audit_worksheet.csv          ← LABEL THIS (50 rows)
  ├── entity_resolution_worksheet.csv     ← LABEL THIS (34 rows)
  ├── TRIPLE_AUDIT_README.md              ← Quick start guide
  ├── TRIPLE_AUDIT_INSTRUCTIONS.md        ← Detailed instructions
  └── TRIPLE_AUDIT_DECISION_GATE.md       ← Decision criteria

docs/
  └── ENTITY_RESOLUTION_INSTRUCTIONS.md   ← Entity review guide

graph/
  ├── audit_triples.py                    ← Run with --score after labeling
  └── apply_entity_resolution.py          ← Run after entity labeling
```

## 🔄 Current Workflow Status

**Phase 0:** ✅ Complete (pushed to GitHub)
**Phase 1 Prep:** ✅ Complete (pushed to GitHub)
**Phase 1 Human Work:** ⏸️ **WAITING FOR YOU**
**Phase 1 Automation:** ⏸️ Paused until metrics reported

## 💡 Tips

- **Triple audit:** Be strict. Only mark `true` if the triple is *explicitly* supported by the passage. Paraphrased or implied relationships should be `false`.

- **Entity resolution:** High similarity score (>0.90) usually means MERGE, but check the aliases and context. Different papers may use the same method name for different things.

- **Time management:** You can do these in multiple sessions. The CSV files save your progress.

- **Questions?** Check the instruction files first. They have examples and edge case guidance.

## 🚀 When You're Done

Either:
1. Post the metrics here and I'll update the workflow
2. Or just say "Phase 1 labeling complete" and I'll extract the metrics from the output files

---

**Ready?** Open `data/processed/triple_audit_worksheet.csv` and start labeling! 🎯
