# Bounded agent controller

`run_agent.py` implements a single-query state machine with a configurable maximum of five planner steps. The planner chooses among keyword, local vector, and bounded graph search, can stop early, and the final answer step abstains when no evidence is retrieved. Citation IDs are checked against the retrieved set; missing or invalid citations force abstention. Planner response IDs, per-step latency, retrieval-tool and answer latency, and model token use are saved with the local run output. Model API cost is reported as zero because all inference is local; this excludes electricity and hardware costs.

After the domain graph files exist and Ollama is running locally:

```powershell
ollama pull qwen3:4b-instruct
python -m pip install -e ".[retrieval]"
python agent/run_agent.py --question "Your research question"
```

Planner and answer inference stay on the local Ollama server; no model API charges apply. The command builds or loads local domain passage embeddings. It has not been run. Its default limits are configured under `[agent]` in `configs/default.toml`; cap tool results or steps before large runs. Domain graph extraction and retrieval evaluation are still prerequisites for meaningful results.
