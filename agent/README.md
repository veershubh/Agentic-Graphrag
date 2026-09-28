# Agent

Reserved for the bounded planning and tool-selection state machine in Phase 4.
# Bounded agent controller

`run_agent.py` implements a single-query state machine with a configurable maximum of five planner steps. The planner chooses among keyword, local vector, and bounded graph search, can stop early, and the final answer step abstains when no evidence is retrieved. Citation IDs are checked against the retrieved set; missing or invalid citations force abstention. Planner and answer token use and latency are saved with the local run output.

After the domain graph files exist, install the optional dependencies and set `OPENAI_API_KEY`:

```powershell
python -m pip install -e ".[api,retrieval]"
python agent/run_agent.py --question "Your research question"
```

This command makes planner and answer model calls and builds/loads local domain passage embeddings. It has not been run. Its default limits are configured under `[agent]` in `configs/default.toml`; cap tool results or steps before large runs. Domain graph extraction and retrieval evaluation are still prerequisites for meaningful results.
