# Labeling Tools — Critical Usage Warning

## ✅ Safe to Use: `interactive_audit.py`

```powershell
python scripts/interactive_audit.py
```

This tool is **read-only AI** — it displays triples and passages clearly, you make all judgments. Safe to use.

- Shows triple + passage
- Press `t` (true) or `f` (false)
- Saves progress, resumes where you left off
- **NO automation** — you judge every triple

## ⚠️ DO NOT AUTO-ACCEPT: `assisted_audit.py`

```powershell
python scripts/assisted_audit.py
```

This tool uses **regex pattern matching** (not actual AI) to suggest labels. It's a **measurement bias hazard**.

### Why This Is Dangerous

**The audit measures extraction precision.** If you accept regex-suggested labels:

1. You're measuring **regex accuracy**, not **extraction accuracy**
2. These correlate but are NOT the same thing
3. Systematic bias: regex looks for word patterns like "uses", misses semantic relationships

### Example of Regex Failure

**Triple:** `(multi-dimensional approach) --[USES]--> (realism)`

**Passage:** "...the evaluation framework proposed in this paper is centered around two dimensions... namely, realism and diversity."

**Regex suggestion:** `FALSE` (no word "uses" found)  
**Actual answer:** `TRUE` (the method uses realism as an evaluation dimension)

### How Regex Works (Not AI)

From `assisted_audit.py` L29-60:

```python
# Look for explicit relationship patterns
patterns = {
    'USES': [
        r'uses.*object',
        r'applies.*object',
        r'employs.*object',
    ],
    ...
}

# Fallback: character distance between entities
distance = abs(subj_pos - obj_pos)
if distance < 100:
    return ('uncertain', 'Entities close but no pattern')
```

This is **substring matching + distance heuristics**, not semantic understanding.

### If You Use It Anyway

**NEVER press ENTER to auto-accept.** Use it only as a reading aid:

1. Read the suggestion
2. Read the passage yourself
3. **Make your own judgment**
4. Press `t` or `f` explicitly (not ENTER)

Pressing ENTER = accepting measurement bias.

## Test Labels Were Contaminated

During tool testing, 2 rows got labeled with simulated input:

- `audit_00e9ae62abc0371b6bfb` → labeled `"false"` (from piped `echo "f"`)
- `audit_0b1d57ba9355fde6bfac` → labeled `"true"` (from piped `echo "t"`)

These were **not human judgments**. I've reset all 50 rows to unlabeled.

## Recommendation

**Use `interactive_audit.py` only.** Budget ~90 minutes for 50 triples.

If you want speed, use assisted mode for **display** but always override:
- Read AI suggestion (to focus your attention)
- Read passage
- Judge yourself
- Press `t` or `f` (never ENTER)

The 30-minute time estimate assumed auto-accepting suggestions. That's measurement contamination. The real time is ~90 minutes for clean data.

---

**Bottom line:** Interactive tool = good. Assisted suggestions = reading aid only, never auto-accept.
