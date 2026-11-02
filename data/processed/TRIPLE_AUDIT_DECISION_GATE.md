# Triple Audit Decision Gate

## Purpose

This document defines the decision criteria for proceeding with knowledge graph extraction based on triple accuracy audit results.

## Critical Background

### Current State
- **Graph retrieval recall@5**: 0.041 (graph-only) vs 0.549 (BM25 baseline)
- **Graph coverage**: 188/677 passages (28%) from 19 papers
- **Triple rejection rate**: 59% (532 accepted, 772 rejected by ontology validation)
- **Entity resolution**: 34 candidate pairs, 13 alias collisions pending review
- **Extraction model**: Qwen3 4B (local, no API costs)

### Why This Audit Matters

Triple accuracy is the **foundation of graph quality**. Without knowing extraction accuracy, we cannot:
1. Diagnose whether poor graph retrieval is due to bad extractions vs other factors
2. Justify scaling extraction to the full 325-paper corpus
3. Determine if entity resolution efforts will yield meaningful improvements
4. Validate prompt engineering investments

## Decision Criteria

### Threshold: 70% Accuracy

**If triple_accuracy ≥ 0.70:**
- ✅ Extraction quality is **acceptable for research prototype**
- ✅ Proceed to prompt improvement testing (Task 1.4)
- ✅ Test improved prompts on small sample (~20 passages)
- ✅ Re-audit improved extractions (25 samples)
- ✅ If improvement shown, scale to full corpus (Task 1.6)

**If triple_accuracy < 0.70:**
- ⚠️ Extraction quality is **below research-grade threshold**
- ⚠️ Task 1.4 (prompt improvement) becomes **CRITICAL PATH**
- ⚠️ Do NOT scale to full corpus until accuracy improves
- ⚠️ Consider alternative extraction models or approaches

### Confidence Interval Interpretation

The audit uses a **Wilson 95% confidence interval** with 50 samples:

| Point Estimate | Typical 95% CI | Interpretation |
|---------------|----------------|----------------|
| 0.90 | [0.78, 0.97] | Excellent; proceed confidently |
| 0.80 | [0.67, 0.90] | Good; minor improvements recommended |
| 0.70 | [0.56, 0.82] | Acceptable threshold; improvements needed |
| 0.60 | [0.46, 0.73] | Below threshold; major improvements required |
| 0.50 | [0.36, 0.64] | Poor; reconsider extraction approach |

**Conservative interpretation**: If the **lower bound** of the 95% CI is below 0.65, treat as failing threshold even if point estimate exceeds 0.70.

## Decision Paths

### Path A: Accuracy ≥ 0.70 (Acceptable Quality)

**Immediate Actions:**
1. ✅ Complete entity resolution audit (Task 1.2)
2. ✅ Analyze error patterns from the 30% failed triples
3. ✅ Design prompt improvements targeting identified errors (Task 1.4)

**Next Phase:**
1. Test improved prompts on 20 new passages
2. Audit 25 triples from improved extraction
3. If accuracy improves by ≥5 percentage points, scale to full corpus
4. If no improvement, proceed with current extraction quality

**Rationale:**
- 70% accuracy is research-grade for a prototype
- Entity resolution may merge duplicates and improve effective accuracy
- Graph retrieval issues may be due to entity linking, not extraction
- Scaling is justified to test coverage hypothesis

### Path B: Accuracy < 0.70 (Below Threshold)

**Immediate Actions:**
1. ⚠️ **HALT** scaling plans (Task 1.6 blocked)
2. ⚠️ Detailed error analysis on all 50 audit samples
3. ⚠️ Categorize errors by type:
   - Entity recognition errors (wrong entities extracted)
   - Relation misclassification (wrong predicate)
   - Hallucinations (unsupported triples)
   - Entity type errors (Method classified as Dataset, etc.)

**Required Improvements (Task 1.4 Critical):**
1. **Prompt Engineering:**
   - Strengthen instructions against hallucination
   - Add few-shot examples of correct extractions
   - Clarify entity type definitions
   - Add explicit rejection criteria

2. **Model Alternatives (if prompt improvements insufficient):**
   - Test Qwen3:8b (5.2 GB, already pulled)
   - Test other local models (Llama 3, Mistral)
   - Consider API models (GPT-4o-mini) for cost/quality tradeoff

3. **Validation Changes:**
   - Tighten ontology constraints
   - Add post-processing filters
   - Implement confidence thresholding

**Re-Audit Requirement:**
- After improvements, extract 30 new passages
- Audit 30 triples (60% of original sample size)
- Target: accuracy ≥ 0.75 to proceed

**Rationale:**
- Sub-70% accuracy compounds entity resolution errors
- Poor extractions waste human adjudication effort
- Graph retrieval cannot succeed with unreliable triples
- Investment in quality now saves time later

## Expected Results Analysis

### Scenario 1: High Accuracy (≥ 0.85)
**Interpretation:** Extraction is working well; graph retrieval issues likely due to:
- Entity linking failures (queries can't find relevant entities)
- Insufficient graph coverage (28% of corpus)
- Traversal or scoring problems

**Action:** Proceed directly to Phase 2 (entity linking improvements) after entity resolution

### Scenario 2: Moderate Accuracy (0.70-0.84)
**Interpretation:** Extraction is acceptable but has room for improvement

**Action:** Parallel track:
- Improve prompts and test (Task 1.4)
- Complete entity resolution (Task 1.2)
- Begin entity linking experiments (Phase 2 overlap)

### Scenario 3: Low Accuracy (< 0.70)
**Interpretation:** Extraction quality is limiting factor; must fix before proceeding

**Action:** Focus entirely on extraction quality (Task 1.4 becomes sole priority)

## Error Pattern Analysis

After audit completion, categorize errors to guide improvements:

### Entity Recognition Errors
- **Symptom:** Wrong entities extracted (names don't match passage)
- **Fix:** Few-shot examples, entity definition clarification

### Relation Misclassification
- **Symptom:** Correct entities but wrong predicate
- **Fix:** Relation definition examples, clearer distinction between predicates

### Hallucinations
- **Symptom:** Triples not supported by passage text
- **Fix:** Stronger grounding instructions, confidence calibration

### Entity Type Errors
- **Symptom:** Correct entity and relation but wrong entity kind
- **Fix:** Ontology examples, type constraints in schema

### Ambiguity Handling
- **Symptom:** Extracting uncertain relationships as confident
- **Fix:** Confidence calibration, rejection criteria

## Scoring Output Format

The audit scoring script generates:

```json
{
  "sample_size": 50,
  "correct_count": 38,
  "triple_accuracy": 0.76,
  "wilson_95_ci": [0.623, 0.869],
  "note": "This is accuracy on the reviewed random sample; it does not measure entity-resolution quality."
}
```

**Key fields:**
- `triple_accuracy`: Point estimate (0-1 scale)
- `wilson_95_ci`: [lower_bound, upper_bound] at 95% confidence
- `correct_count`: Number of triples marked as correct

## Integration with Other Tasks

### Task 1.2 (Entity Resolution)
- **If accuracy ≥ 0.70:** Proceed in parallel
- **If accuracy < 0.70:** Still proceed (entity resolution is independent issue)

### Task 1.4 (Prompt Improvement)
- **If accuracy ≥ 0.70:** Optional optimization
- **If accuracy < 0.70:** Critical path blocker

### Task 1.6 (Scale Extraction)
- **If accuracy ≥ 0.70:** Conditional go (test improvements first)
- **If accuracy < 0.70:** Blocked until accuracy improves

### Phase 2 (Graph Retrieval)
- **If accuracy ≥ 0.70:** Can begin entity linking experiments
- **If accuracy < 0.70:** Premature; fix extraction first

## Timeline Implications

### High Accuracy Path (≥ 0.85)
- Entity resolution: 2-3 days
- Prompt improvements: 1-2 days (optional)
- Scale extraction: 2-3 days
- **Total to Phase 2:** ~5-8 days

### Moderate Accuracy Path (0.70-0.84)
- Entity resolution: 2-3 days
- Prompt improvements: 2-3 days
- Re-test and audit: 1 day
- Scale extraction: 2-3 days
- **Total to Phase 2:** ~7-12 days

### Low Accuracy Path (< 0.70)
- Error analysis: 1 day
- Prompt engineering: 3-5 days
- Model testing: 2-3 days
- Re-extraction and audit: 1-2 days
- Entity resolution: 2-3 days
- Scale extraction: 2-3 days
- **Total to Phase 2:** ~11-19 days

## Reporting Template

After audit completion, report results using this template:

---

**Triple Audit Results - [Date]**

**Sample:** 50 randomly selected edge-evidence pairs

**Results:**
- Triple Accuracy: X.XX (XX%)
- Wilson 95% CI: [X.XX, X.XX]
- Correct: XX/50
- Incorrect: XX/50

**Decision:** [PASS / FAIL threshold]

**Error Breakdown:**
- Entity recognition: XX
- Relation misclassification: XX
- Hallucinations: XX
- Entity type errors: XX
- Other: XX

**Recommended Actions:**
1. [Action based on results]
2. [Action based on results]
3. [Action based on results]

**Next Steps:**
- [Task 1.2 / Task 1.4 / Task 1.6 status]

---

## References

- Wilson Score Interval: [Wikipedia](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval)
- Graph Extraction README: `graph/README.md`
- Implementation Roadmap: `docs/IMPLEMENTATION_ROADMAP.md` (Phase 1)
- Ontology Definition: `graph/ontology.py`

## Version History

- v1.0 (2025-01-XX): Initial decision gate definition for Task 1.1
