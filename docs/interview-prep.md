# Interview preparation notes

Use these as evidence-based talking points, not memorized claims. The current domain corpus and graph remain provisional and unaudited.

## Resume bullet (draft)

Built a local multi-hop RAG evaluation pipeline over 300 MuSiQue and 98 domain questions with hop-split confidence intervals and a GitHub Actions retrieval gate; BM25+dense RRF improved public recall@5 from 0.429 to 0.4925, while domain graph-only recall@5 was 0.041 versus BM25's 0.549, showing why graph quality must be audited before claiming a gain.

## Why use a constrained extraction schema?

The graph needs stable entity types and a small relation vocabulary so triples can be validated and linked back to source chunks. The schema rejects unsupported endpoint combinations before they enter the graph. In the 197-passage pilot, 636 of 1,362 candidate triples passed validation and 726 were rejected. That validates the guardrail's ability to catch invalid candidates; it does not establish extraction precision. A 50-triple human audit and larger labeled sample are still needed.

## How was entity resolution validated?

Names are normalized for case and punctuation, embedding similarity produces candidate pairs, and a conservative alias table avoids merging ambiguous names automatically. The pilot produced 307 review pairs and 103 unresolved collisions. Since those pairs have not been hand-labeled, the project cannot report entity-resolution precision or recall yet. The next step is to label at least 100 pairs and report both metrics.

## When did the agent beat the fixed hybrid, and at what cost?

It has not shown a validated win. On three same-question pilot items, the agent scored token F1 0.222 versus 0.315 for BM25 and took 77.4 seconds end to end versus 14.4 seconds. The fixed hybrid scored 0.289 versus BM25's 0.287 on a different 30-question sample, but the paired difference was +0.002 with a 95% interval of -0.074 to +0.080. Both use local models with zero hosted API charges; electricity, hardware, and latency are still real costs.

## What regression did CI catch?

No historical retrieval regression has been recorded as caught by CI. The current GitHub Actions gate runs deterministic unit checks and the public 300-question BM25 evaluation, then fails if overall or 2-, 3-, or 4-hop recall drops below configured floors. It is a useful tripwire, not a graph, answer-F1, or faithfulness gate.

## What would you do differently?

I would review corpus relevance and rights, then label extraction and entity-resolution samples before scaling graph construction. The early pilot was useful for finding integration issues, but hundreds of unaudited graph nodes cannot explain a low graph retrieval score. I would also keep answer failures and retrieval failures separate by inspecting traces and evidence, not relying on exact match alone.
