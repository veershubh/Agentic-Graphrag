# Extraction Failure Analysis - Triple Audit Results

**Date:** November 2, 2026  
**Audit Sample:** 50 random triples  
**Accuracy:** 66% (33/50 correct, 17/50 incorrect)  
**Wilson 95% CI:** 52.2% – 77.6%  

## Failure Categories

### Category 1: Paper vs Method/Benchmark Confusion (10/17 = 59%)

**Problem:** Paper titles are extracted as Paper entities, then treated as if they were Methods or Benchmarks.

**Examples:**
- `(TrGLUE [Paper]) --[USES]--> (CoLA [Task])` 
  - TrGLUE is a paper title, not a method
  - Should be: `(TrGLUE benchmark [Method]) --[EVALUATES_ON]--> (CoLA [Task])`

- `(TrGLUE [Paper]) --[EVALUATES_ON]--> (STS-B [Task])`
  - Same issue - TrGLUE is used as both paper name and benchmark name

**Root cause:** The ontology doesn't distinguish between:
- Paper (the publication)
- Method/Benchmark (the contribution described in the paper)

**Count in failures:** 10/17 (TrGLUE appears in 5 failures, long paper titles in 3)

### Category 2: Implicit Relationships (4/17 = 24%)

**Problem:** Entities are mentioned together in the passage but the relationship is implied, not explicitly stated.

**Examples:**
- `(Simulator K [Method]) --[USES]--> (item reranking [Task])`
  - Passage mentions both but doesn't say Simulator K "uses" item reranking

- `(CoT prompting [Method]) --[USES]--> (few-shot [Task])`
  - Both mentioned in context but no explicit "uses" statement

**Root cause:** Extraction prompt doesn't emphasize "explicitly stated" relationships.

### Category 3: Wrong Entity Type (2/17 = 12%)

**Problem:** Things classified as Tasks that aren't tasks.

**Examples:**
- `(Discriminator [Method]) --[EVALUATES_ON]--> (human-generated [Task])`
  - "human-generated" is a data type/label, not a task

**Root cause:** Task definition is too broad.

### Category 4: Subject Not in Passage (3/17 = 18%)

**Problem:** The subject entity name doesn't appear in the passage at all.

**Examples:**
- `(Evaluating LLM Reasoning... [Paper]) --[PROPOSES]--> (formulate optimization models [Method])`
  - Full paper title not in passage
  
- `(Introducing TrGLUE... [Paper]) --[USES]--> (Amazon Translate [Method])`
  - Long paper title not in this specific passage

**Root cause:** Entity extraction happens at document level but relationship extraction happens at passage level.

## Recommendations for Prompt v3

### 1. Clarify Paper vs Method Distinction

Add to prompt:
```
**CRITICAL DISTINCTION:**
- Paper: The publication itself (e.g., "2212.08037", "Smith et al. 2023")
- Method: The approach/system/benchmark DESCRIBED in the paper (e.g., "TrGLUE benchmark", "BERT model")

If a paper proposes a method with the same name, extract BOTH:
- Paper entity: "TrGLUE" [Paper]
- Method entity: "TrGLUE benchmark" or "TrGLUE evaluation suite" [Method]

Do NOT use paper titles as subjects in USES or EVALUATES_ON relationships.
```

### 2. Emphasize Explicit Relationships

Change from:
```
Extract relationships between entities
```

To:
```
Extract ONLY relationships that are EXPLICITLY STATED in the passage.
- ✅ "BERT uses WordPiece tokenization" → (BERT, USES, WordPiece)
- ❌ "We use BERT for classification" → Do not extract (BERT, USES, classification) 
     because the METHOD uses BERT, not BERT using classification
```

### 3. Tighten Task Definition

Change from:
```
Task: A problem or benchmark (e.g., NER, sentiment analysis, ImageNet)
```

To:
```
Task: A well-defined NLP/ML problem or benchmark dataset
- ✅ sentiment analysis, named entity recognition, GLUE benchmark
- ❌ "human-generated" (data type), "few-shot" (learning paradigm), "optimization" (too broad)
```

### 4. Require Subject Presence

Add validation:
```
BEFORE extracting a triple:
1. Verify both subject AND object entity names appear in this passage
2. If subject is missing, DO NOT extract the triple
3. Confidence < 0.60 if entities are >100 words apart
```

## Expected Impact

If we address Category 1 alone (10/17 failures), accuracy would improve from 66% → **76%** (38/50 correct).

Adding Categories 2-4 could reach **80-85%** accuracy.

## Next Steps

1. Update extraction prompt to v3 with above changes
2. Test on 20-passage validation set (different papers from pilot)
3. Hand-audit 20 new triples
4. If accuracy ≥ 75%, proceed to full re-extraction
5. If < 75%, iterate on prompt again
