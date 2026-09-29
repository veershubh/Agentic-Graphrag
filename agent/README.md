# Bounded agent controller

`run_agent.py` implements a single-query state machine with a configurable maximum of five planner steps. The planner chooses among keyword, local vector, and bounded graph search, can stop early, and the final answer step abstains when no evidence is retrieved. Citation IDs are checked against the retrieved set; missing or invalid citations force abstention. Planner response IDs, per-step latency, retrieval-tool and answer latency, and model token use are saved with the local run output. Model API cost is reported as zero because all inference is local; this excludes electricity and hardware costs.

After the domain graph files exist and Ollama is running locally:

```powershell
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b
python -m pip install -e ".[retrieval]"
python agent/run_agent.py --question "Your research question"
```

Planner and answer inference stay on the local Ollama server; planning defaults to Qwen3 4B and answering to Qwen3 8B, with no model API charges. The command builds or loads local domain passage embeddings. One verified domain question completed in 94 seconds with the embedding cache warm, returned “human ratings” for the gold “Human annotations,” and cited the relevant source passages. The first run spent about 14 minutes building the 10,878-passage embedding cache; later runs reuse it. A short planner query is replaced with the original question, and answer context prioritizes recent search results to reduce noise. This single query confirms the path is wired but does not measure general answer accuracy. The graph retrieval diagnostic underperformed BM25, so graph-assisted answers need more graph coverage and quality work.
