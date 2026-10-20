# What a small graph pilot taught me about multi-hop RAG

*Draft for review. The full-inventory graph run is still in progress; this draft reports only completed, versioned experiments.*

I started this project with a practical question: does linking papers, methods, datasets, and metrics in a knowledge graph improve evidence retrieval enough to justify the extra machinery?

I built two separate evaluation tracks. The public track uses a frozen 300-question MuSiQue slice. The domain track uses 98 answerable questions over a provisional research-paper collection, split by hop count. I kept the tracks separate and evaluated supporting-document recall rather than treating a retrieved passage as proof that a generated answer was correct.

The public results were encouraging for dense retrieval: BM25 reached recall@5 of 0.429, dense retrieval 0.482, and BM25 plus dense reciprocal-rank fusion 0.4925. The domain results looked very different. BM25 reached 0.549, while dense retrieval reached 0.175 and graph-only retrieval 0.041. BM25 plus graph fusion reached 0.435. These measurements made it important to check data and ID alignment before calling the graph a bad idea; they are not directly comparable across tracks.

The graph pilot processed 197 passages from 20 papers. It produced 1,734 entity mentions and 1,362 candidate triples; ontology and endpoint checks accepted 636 and rejected 726. Consolidation yielded 994 nodes and 581 edges, with unresolved aliases still needing review. That is a useful engineering result, but not evidence of a trustworthy graph: no hand-labeled extraction or entity-resolution audit has been completed.

Answer quality told a similarly mixed story. On the same stratified 30-question domain sample, BM25 answers had token F1 0.287 and the fixed hybrid had 0.289. The paired difference was only +0.002, with a 95% interval from -0.074 to +0.080. A three-question agent wiring pilot scored F1 0.222 versus 0.315 for BM25 and took 77.4 seconds per query end to end versus 14.4 seconds. I have no evidence that the agent beats the fixed hybrid.

The most useful lesson so far is that graph quality has to be measured before graph retrieval is blamed. Extraction validation rejected many candidate triples, entity-resolution candidates have not been hand-labeled, and the current domain corpus still needs relevance and rights review. I also found answer-generation failures even when the annotated support passage was ranked first, so retrieval metrics alone cannot explain the full system.

The work runs locally with Ollama and incurs zero hosted model API charges. That does not make it costless: model downloads, GPU time, electricity, latency, and local hardware still matter. One local agent query took 94 seconds, and the current full-inventory extraction is running from a resumable cache. Its final graph metrics are intentionally absent from this draft until extraction, merge, and evaluation finish.

The next steps are to complete that extraction, evaluate the graph on the same frozen questions, and then hand-audit extraction and entity-resolution accuracy before making a stronger claim. The current result is not that GraphRAG works or fails in general. It is that the pipeline needs better evidence and a more disciplined audit before the domain negative result is ready to report.

*Reproduction commands and complete confidence intervals are in the [results summary](../eval/results-summary.md).*
