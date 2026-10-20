# Full-coverage graph retrieval comparison

Same 98 domain questions and passage corpus; values are supporting-document recall@5.
Each cell shows `before → after (change)`. Positive change is higher recall; it is descriptive, not a significance claim.

- Before: `domain_retrieval_after_debug.json` (994 nodes, 581 edges)
- After: `domain_graph_full_10_per_paper_after_debug_verified.json` (10798 nodes, 6637 edges)
- Passage count: 10878 before; 10878 after

| Variant | 1-hop R@5 (before → after, Δ) | 2-hop R@5 (before → after, Δ) | 3-hop R@5 (before → after, Δ) | Overall R@5 (before → after, Δ) |
| --- | ---: | ---: | ---: | ---: |
| bm25 | 0.816 → 0.816 (+0.000) | 0.450 → 0.450 (+0.000) | 0.311 → 0.311 (+0.000) | 0.549 → 0.549 (+0.000) |
| graph | 0.026 → 0.605 (+0.579) | 0.067 → 0.183 (+0.117) | 0.033 → 0.189 (+0.156) | 0.041 → 0.349 (+0.308) |
| bm25_graph_rrf | 0.632 → 0.816 (+0.184) | 0.400 → 0.483 (+0.083) | 0.222 → 0.389 (+0.167) | 0.435 → 0.583 (+0.148) |
| dense | 0.395 → 0.395 (+0.000) | 0.133 → 0.133 (+0.000) | 0.100 → 0.100 (+0.000) | 0.224 → 0.224 (+0.000) |
| bm25_dense_rrf | 0.632 → 0.632 (+0.000) | 0.300 → 0.300 (+0.000) | 0.200 → 0.200 (+0.000) | 0.398 → 0.398 (+0.000) |
| bm25_dense_graph_rrf | 0.605 → 0.763 (+0.158) | 0.350 → 0.417 (+0.067) | 0.222 → 0.311 (+0.089) | 0.410 → 0.519 (+0.109) |
| dense_entity_graph | 0.026 → 0.500 (+0.474) | 0.033 → 0.217 (+0.183) | 0.011 → 0.178 (+0.167) | 0.024 → 0.315 (+0.291) |
| bm25_dense_entity_graph_rrf | 0.632 → 0.737 (+0.105) | 0.333 → 0.383 (+0.050) | 0.211 → 0.267 (+0.056) | 0.412 → 0.485 (+0.073) |

The domain corpus and graph remain provisional pending relevance/rights review and manual extraction/entity-resolution audits.
