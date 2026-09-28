# Bounded agent controller

`run_agent.py` implements a single-query state machine with a configurable maximum of five planner steps. The planner chooses among keyword, local vector, and bounded graph search, can stop early, and the final answer step abstains when no evidence is retrieved. Citation IDs are checked against the retrieved set; missing or invalid citations force abstention. Planner response IDs, per-step latency, retrieval-tool and answer latency, and model token use are saved with the local run output. Optional estimated costs are calculated only when current token rates are configured under `[agent]`.

After the domain graph files exist, install the optional dependencies and set `OPENAI_API_KEY`:

```powershell
python -m pip install -e ".[api,retrieval]"
python agent/run_agent.py --question "Your research question"
```

This command makes planner and answer model calls and builds or loads local domain passage embeddings. It has not been run. Its default limits are configured under `[agent]` in `configs/default.toml`; cap tool results or steps before large runs. Domain graph extraction and retrieval evaluation are still prerequisites for meaningful results.
