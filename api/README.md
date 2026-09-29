# Local API

`app.py` exposes the local agent through `GET /healthz` and `POST /ask`. It only accepts loopback Ollama endpoints, limits each request to 1,000 characters, allows one concurrent agent run by default, rate-limits to five requests per minute, and applies a 15-minute request timeout. The agent's temporary output is removed after the response is formed. Requests stay on the machine; model API cost is $0. Local model downloads, hardware, and electricity are separate costs.

## Run locally

The local domain passages and graph files must already exist, and Ollama must have the configured Qwen3 models. From the repository root:

```powershell
python -m pip install -e ".[api,retrieval]"
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Check local readiness and ask a question:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask -ContentType "application/json" -Body '{"question":"What did the Attributed QA study use as its gold standard?"}'
```

The response includes the answer or abstention, citations, the planner's selected tools and search queries, stop reason, and elapsed time. Concurrency, rate, and timeout controls can be adjusted with `GRAPHRAG_MAX_CONCURRENCY`, `GRAPHRAG_REQUESTS_PER_MINUTE`, and `GRAPHRAG_REQUEST_TIMEOUT_SECONDS`. Keep the server bound to `127.0.0.1`; authentication, TLS, public deployment, and request-queue persistence are not implemented. Each request starts the CLI process and reloads the local embedding model, so expect substantial latency even while Ollama keeps its language model warm.
