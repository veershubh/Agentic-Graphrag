# Entity Resolution Adjudication Instructions

## Overview

This worksheet contains entity pairs that may represent the same real-world entity. Your task is to review each pair and decide whether they should be merged.

**Critical**: Entity resolution precision must be ≥0.90 (no incorrect merges). It is better to keep entities separate than to merge them incorrectly.

## File Location

- **Worksheet**: `data/processed/entity_resolution_worksheet.csv`
- **Original candidates**: `data/processed/entity_resolution_candidates.jsonl`

## Adjudication Process

For each pair in the worksheet:

1. **Review the evidence**:
   - Compare `entity1_name` and `entity2_name`
   - Review `entity1_aliases` and `entity2_aliases`
   - Check `entity1_type` and `entity2_type` (must match)
   - Note `shared_aliases` (indicates potential overlap)
   - Examine `source_chunk_ids` to understand context
   - Check `paper_ids` to see if they appear in same papers
   - Consider `similarity_score` (higher = more similar names)

2. **Make a decision** in the `decision` column:
   - **MERGE**: These represent the same real-world entity
   - **KEEP_SEPARATE**: These are different entities despite similarity
   - **UNCERTAIN**: Need more information or expert review

3. **For MERGE decisions**:
   - Set `canonical_entity_id` to the preferred entity ID
   - Usually choose the entity with:
     - More source chunks (more provenance)
     - More specific/standard name
     - Earlier occurrence in the corpus
   - Example: If entity1 has 5 source chunks and entity2 has 2, set `canonical_entity_id` to `entity1_id`

4. **Document reasoning** in the `notes` column:
   - Explain why you merged or kept separate
   - Note any ambiguity or edge cases
   - Flag pairs that need expert domain review

## Decision Guidelines

### Clear MERGE Cases

These are strong indicators for merging:

- **Exact match with formatting differences**:
  - "LLaMA-2-7B" vs "LLaMA 2 7B"
  - "BERT-base" vs "BERT Base"
  
- **Singular/plural variants**:
  - "politeness judgment" vs "politeness judgments"
  - "classification task" vs "classification tasks"
  
- **Acronym expansion**:
  - "NLP" vs "Natural Language Processing" (if same entity in context)
  
- **Version notation variants**:
  - "GPT-4" vs "GPT4" (referring to same model version)

- **High similarity (>0.95) + shared context**:
  - Same paper or adjacent passages
  - Shared aliases beyond generic terms

### Clear KEEP_SEPARATE Cases

Do NOT merge in these situations:

- **Different versions of same family**:
  - "Llama2-7B-Chat" vs "Llama2-13B-Chat" (different model sizes)
  - "GPT-3" vs "GPT-4" (different versions)
  
- **Different variants**:
  - "BERT-base" vs "BERT-large"
  - "meta-llama/llama-3-8b-instruct" vs "meta-llama/llama-3.1-8b-instruct"
  
- **Generic shared aliases only**:
  - Two datasets both tagged with "dataset"
  - Two methods both tagged with "method"
  
- **Same type but different entities**:
  - "sentiment analysis" vs "emotion classification" (both tasks)
  - "accuracy" vs "F1-score" (both metrics)

- **Low confidence despite high similarity**:
  - Names are similar but appear in completely different contexts
  - No shared papers or adjacent passages

### Borderline UNCERTAIN Cases

Mark as UNCERTAIN when:

- Names are very similar but context is ambiguous
- One entity has minimal provenance (1 chunk only)
- Aliases conflict or are inconsistent
- High similarity but different papers with no cross-references
- Domain expertise needed to distinguish variants

## Precision Requirement

**Target: ≥90% precision (≤10% false merge rate)**

- **False merge (incorrect MERGE)**: Merging two distinct entities loses information and corrupts the graph
- **False keep-separate (incorrect KEEP_SEPARATE)**: Keeping duplicates is less harmful; duplicates can be found and merged later

**When in doubt, KEEP_SEPARATE or mark UNCERTAIN.**

## Examples

### Example 1: Clear MERGE
```
entity1_name: "LLM politeness judgment"
entity2_name: "LLM politeness judgments"
similarity_score: 0.9539
shared_aliases: ["method"]
decision: MERGE
canonical_entity_id: method_0d21f6d163a34f497dbf
notes: Singular/plural variant of same method
```

### Example 2: Clear KEEP_SEPARATE
```
entity1_name: "Llama2-7B-Chat"
entity2_name: "Llama2-13B-Chat"
similarity_score: 0.9571
shared_aliases: []
decision: KEEP_SEPARATE
canonical_entity_id: 
notes: Different model sizes (7B vs 13B parameters)
```

### Example 3: Borderline UNCERTAIN
```
entity1_name: "Llama3.1"
entity2_name: "Llama3"
similarity_score: 0.9709
shared_aliases: ["method"]
decision: UNCERTAIN
canonical_entity_id: 
notes: Could be version difference (3.1 vs 3.0) or informal reference to same family. Need to check source passages for context.
```

## After Adjudication

1. Save the completed worksheet as CSV
2. Ensure all rows have a decision (MERGE/KEEP_SEPARATE/UNCERTAIN)
3. Ensure all MERGE decisions have a valid `canonical_entity_id`
4. Run the resolution application script:
   ```powershell
   python graph/apply_entity_resolution.py
   ```

## Quality Checks

Before running the application script, verify:

- [ ] All candidates reviewed (no UNREVIEWED status)
- [ ] All MERGE decisions have canonical_entity_id set
- [ ] Canonical entity IDs are valid (exist in nodes file)
- [ ] Notes explain reasoning for borderline cases
- [ ] Precision target met (≥90% confidence in MERGE decisions)

## Alias Collision Reduction Target

Current state: **103 unresolved alias collisions**

Target: **≥50% reduction** (to ≤51 collisions)

Effective entity resolution will consolidate entities sharing ambiguous aliases, reducing collisions when multiple entities claim the same alias.
