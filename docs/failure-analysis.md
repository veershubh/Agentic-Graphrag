# Domain answer failure triage

This is a first-pass review of the existing 30-question, stratified BM25 answer run in `eval/results/domain_answer_qwen3_8b_stratified_v0.1.json`. It reads the frozen question/supporting-passage IDs and the saved answers; it does not change either input. All 30 rows have exact match 0.000, so exact match alone cannot distinguish retrieval failures from answer or metric failures.

## Evidence coverage

Coverage is the fraction of each question's gold supporting passage IDs present in the saved top-5 `retrieved_ids`.

| Hop count | n | All gold support IDs retrieved | Partial support retrieved | No gold support retrieved |
|---:|---:|---:|---:|---:|
| 1 | 10 | 8 | 0 | 2 |
| 2 | 10 | 1 | 8 | 1 |
| 3 | 10 | 0 | 9 | 1 |
| **Total** | **30** | **9** | **17** | **4** |

Thus 21/30 misses have at least one gold supporting passage absent from top-5. Nine further exact-match misses have every annotated support ID in top-5; those need answer-semantic review because EM can penalize acceptable wording. The support IDs are annotations for evidence sources, not a complete relevance judgment of every retrieved passage.

## Per-question triage

`All support present` and `Some support missing` are observable retrieval facts. They are not definitive root-cause labels: for example, a question may be answerable from one of several support passages, and an answer may be semantically right while scoring EM 0. Token F1 is included as a diagnostic, not as a human correctness label.

| Question | Hops | Support recall@5 | Token F1 | Triage |
|---|---:|---:|---:|---|
| domain-0001 | 1 | 1.000 | 0.250 | All support present; semantic/EM review |
| domain-0002 | 1 | 1.000 | 0.133 | All support present; semantic/EM review |
| domain-0003 | 1 | 0.000 | 0.600 | No gold support retrieved |
| domain-0004 | 1 | 0.000 | 0.143 | No gold support retrieved |
| domain-0005 | 1 | 1.000 | 0.500 | All support present; semantic/EM review |
| domain-0006 | 1 | 1.000 | 0.571 | All support present; semantic/EM review |
| domain-0007 | 1 | 1.000 | 0.750 | All support present; semantic/EM review |
| domain-0008 | 1 | 1.000 | 0.000 | All support present; clear answer-generation failure |
| domain-0011 | 1 | 1.000 | 0.286 | All support present; semantic/EM review |
| domain-0012 | 1 | 1.000 | 0.200 | All support present; semantic/EM review |
| domain-0021 | 2 | 0.500 | 0.600 | Partial support; answer includes both requested parts |
| domain-0022 | 2 | 0.500 | 0.250 | Partial support; synthesis/retrieval review |
| domain-0023 | 3 | 0.333 | 0.095 | Partial support; synthesis/retrieval review |
| domain-0024 | 2 | 0.500 | 0.583 | Partial support; answer includes requested quantities |
| domain-0025 | 3 | 0.667 | 0.148 | Partial support; synthesis/retrieval review |
| domain-0026 | 2 | 0.500 | 0.345 | Partial support; synthesis/retrieval review |
| domain-0027 | 2 | 0.000 | 0.164 | No gold support; off-question answer |
| domain-0028 | 2 | 0.500 | 0.400 | Partial support; synthesis/retrieval review |
| domain-0029 | 2 | 0.500 | 0.244 | Partial support; synthesis/retrieval review |
| domain-0030 | 2 | 1.000 | 0.667 | All support present; semantic/EM review |
| domain-0031 | 2 | 0.500 | 0.583 | Partial support; synthesis/retrieval review |
| domain-0032 | 3 | 0.333 | 0.320 | Partial support; synthesis/retrieval review |
| domain-0033 | 2 | 0.500 | 0.000 | Partial support; answer-generation review |
| domain-0038 | 3 | 0.333 | 0.296 | Partial support; synthesis/retrieval review |
| domain-0046 | 3 | 0.333 | 0.013 | Partial support; answer-generation review |
| domain-0055 | 3 | 0.667 | 0.000 | Partial support; answer-generation review |
| domain-0066 | 3 | 0.333 | 0.062 | Partial support; answer-generation review |
| domain-0076 | 3 | 0.333 | 0.000 | Partial support; answer-generation review |
| domain-0077 | 3 | 0.333 | 0.000 | Partial support; answer-generation review |
| domain-0078 | 3 | 0.000 | 0.400 | No gold support retrieved |

## Concrete examples

- **domain-0001, one hop — metric false negative.** The gold answer is “Human annotations.” The prediction says, “The authors used human annotations as the gold standard for evaluating attribution in the Attributed QA study.” Its supporting passage is in top-5, but normalized-string EM is 0. This is a correct answer under ordinary semantic reading and should not be reported as a factual miss without human review.
- **domain-0008, one hop — answer generation error.** The question asks what kind of reasoning StructTest benchmarks. The annotated support passage is top-1, but the prediction is “The next new moon will occur on June 30.” Retrieval coverage is complete; this is a clear generation failure.
- **domain-0004, one hop — evidence retrieval gap.** Neither gold passage ID is in top-5. The answer names “self-consistency” and “models' self-evaluation ability,” while the gold approaches are multi-way comparison and point-wise evaluation. This case has both missing evidence and an incorrect answer.
- **domain-0021, two hops — incomplete annotated coverage with a plausible answer.** Only one of two gold support IDs is in top-5 (recall 0.5). The saved answer names the retriever bottleneck and all five Blame Game configurations. A top-5 support-recall miss did not prevent this answer from containing both requested facts; inspect the actual cited passages before assigning a root cause.
- **domain-0027, two hops — retrieval and answer-control failure.** No gold support ID is in top-5. The question asks about BIPIA's two model weaknesses and T-Eval's review subprocess, but the prediction instead elaborates on a fake-antivirus prompt-injection example. This is off-question and unsupported by the annotated gold sources; the saved record alone does not establish which retrieved text caused the response.
- **domain-0046, three hops — multi-hop retrieval/synthesis failure.** Only the GLUE-X support ID is retrieved (1/3). The answer gives a long generic GLUE-X description and omits Context Variance's UCM metric and Marathon's multiple-choice format. The evidence coverage and response show both missing sources and poor focus.
- **domain-0078, three hops — complete support miss.** None of the three gold passages is in top-5. The prediction gets the test-agent roles and PSC but gives “142k” instead of “7,072 prompts.” Retrieval coverage is zero and the numeric answer is wrong; the available record does not tell whether the correct facts were recoverable from non-gold retrieved passages.

## Limits and next review

This triage does not assign graph extraction misses, entity-resolution errors, planner decomposition errors, or graph expansion noise: the source run is the BM25 answer baseline, not a graph-agent trace. The plan's graph-specific 30–50-case causal review and human verification remain open. Before treating the provisional labels as audited, review cited/retrieved passage text and answer semantics, especially for full-support EM misses and multi-hop questions whose answer is correct despite partial support recall.
