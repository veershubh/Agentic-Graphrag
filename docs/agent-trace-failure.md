# Agent trace: repeated keyword planning

This is a trace-level review of the local CLI run saved as `data/processed/agent_query.json`. The local output file is ignored and is not committed; the relevant trace fields are summarized here.

## Symptom

The run took 94.45 seconds and used two planner calls for a one-hop question. The answer had a valid citation. Step 1's keyword search took 0.42 seconds and returned five passage IDs, including the annotated gold passage `passage_b21ff60c2d5b62fd06f695d9`. Step 2 returned no retrieval results and ended with `stop_reason=repeated_tool_query`.

## Root cause

The first planner response supplied the one-word query `keyword` instead of a search phrase. `agent/run_agent.py` detects fewer than three content tokens and replaces that value with the original question (`short_planner_query` fallback). After step 1, the planner requested keyword search again with the same question. The visited-query guard detected the duplicate and stopped before running another retrieval tool. The second planner call cost 3.59 seconds; no second search ran.

This was a control inefficiency, not a missed-evidence failure: the first search already returned the gold passage and the final citation was valid. The repeat guard prevented duplicate retrieval. The trace therefore does not justify changing retrieval scoring or the query fallback.

## Trace evidence

| Step | Planner latency | Planner query | Executed query | Tool results | Outcome |
|---:|---:|---|---|---:|---|
| 1 | 14.77s | `keyword` | Original question (fallback) | 5, including gold passage | Continue |
| 2 | 3.59s | Original question | Original question | 0 (tool not executed) | Repeated-query stop |

Total run latency was 94.45s, with 18.36s of planner time, 0.42s of search time, and 35.60s of answer-model time. Local model API cost was $0. Response IDs and per-step token/latency fields are in the ignored local trace. The controller behavior is implemented in `agent/run_agent.py` around the short-query fallback and visited-query guard.

## Limit

This is one CLI trace and one question, not a representative agent evaluation. It does not isolate graph extraction, entity linking, or graph expansion causes. Broader agent evaluation and measured resource use remain open.
