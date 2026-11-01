# Agentic GraphRAG Quickstart

This guide provides step-by-step instructions to set up and run the Agentic GraphRAG system from a clean checkout.

## Prerequisites

- **Python 3.11 or higher**
- **Ollama** for local LLM inference
- **Git** (for cloning the repository)
- **10GB+ free disk space** (for models and data)

## Step 1: Clone and Install

```bash
# Clone the repository
cd c:\Users\Vaishnavi\Desktop\Agentic-Graphrag
cd Agentic-Graphrag

# Install the package in editable mode with optional dependencies
pip install -e ".[papers,retrieval,dev]"
```

## Step 2: Install and Configure Ollama

1. **Download Ollama** from [ollama.ai](https://ollama.ai) and install it.

2. **Pull required models:**

```bash
# Extraction model (used for graph extraction)
ollama pull qwen2.5:14b

# Planning model (used for agent reasoning)
ollama pull qwen2.5:32b

# Answer model (used for final answer generation)
ollama pull qwen2.5:14b
```

3. **Start Ollama server** (if not already running):

```bash
ollama serve
```

Ollama should be available at `http://127.0.0.1:11434` (default).

## Step 3: Verify Data Files

The repository should contain pre-processed data files in `data/processed/`:

```
data/processed/
├── domain_inventory_passages_v1.0.jsonl  # Passage chunks
├── domain_graph_nodes.jsonl              # Graph entities
└── domain_graph_edges.jsonl              # Graph relationships
```

To verify these files exist:

```bash
ls data/processed/*.jsonl
```

If files are missing, you'll need to run the ingestion pipeline (see `docs/IMPLEMENTATION_ROADMAP.md`).

## Step 4: Run Smoke Test

Test the agent with a single question:

```bash
python agent/run_agent.py --question "What methods are evaluated on ImageNet?"
```

**Expected output:** A JSON file at `data/processed/agent_query.json` containing:
- `question`: Your input question
- `answer`: The generated answer (or empty if abstained)
- `citation_ids`: List of passage IDs used to generate the answer
- `abstained`: Boolean indicating whether the agent abstained from answering
- `steps`: List of agent search steps with tool calls (keyword, vector, graph)
- `retrieved`: List of retrieved passages with scores
- `usage`: Token counts and latency information

**Success indicators:**
- JSON file is created without errors
- `abstained` is `false` and `answer` is non-empty, OR
- `abstained` is `true` with empty `answer` (valid if insufficient evidence)
- Multiple `steps` show agent search behavior

## Step 5: Run Unit Tests

Verify the system is working correctly:

```bash
pytest tests/ -v
```

**Expected output:** All tests should pass (116 tests as of v0.1.0).

## Step 6: (Optional) Run Retrieval Evaluation

Evaluate retrieval performance on the MuSiQue public benchmark:

```bash
# Download MuSiQue data (runs once)
python eval/download_public_data.py

# Run retrieval evaluation
python eval/run_retrieval_eval.py
```

**Expected output:** JSON file at `eval/results/musique/retrieval_bm25_v*.json` with:
- `recall_at_k`: Retrieval recall metrics
- `bootstrap_intervals`: Confidence intervals
- `question_count`: Number of evaluated questions

## Step 7: (Optional) Start API and UI

### Prerequisites Checklist

Before starting the API, verify:

- ✅ Ollama is installed and running (`ollama serve`)
- ✅ Required models are pulled:
  ```bash
  ollama pull llama3.2:3b-instruct-fp16
  ollama pull nomic-embed-text
  ```
- ✅ Data files exist in `data/processed/`:
  - `domain_inventory_passages_v1.0.jsonl`
  - `domain_graph_nodes.jsonl`
  - `domain_graph_edges.jsonl`
- ✅ API dependencies installed:
  ```bash
  pip install -e ".[api]"
  ```

### Start API Server

```powershell
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

The API will start on `http://127.0.0.1:8000` and serve the UI at the root path.

### Browser Testing Checklist

**⚠️ Manual verification required by user with Ollama running locally.**

Open your browser to [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and complete the following verification steps:

#### 1. Health Check
- Navigate to [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- Verify JSON response with status "ok" and service versions
- Expected response:
  ```json
  {
    "status": "ok",
    "ollama": "connected",
    "data_loaded": true
  }
  ```

#### 2. UI Load Test
- Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Verify page loads without errors
- Check browser console (F12) for JavaScript errors
- Confirm UI elements are visible:
  - Question input field
  - "Ask" button
  - Empty response area

#### 3. Submit Test Questions

Test with at least 3 different questions to verify various response types:

**Test Question 1: Factual Query**
- Question: `What is BERT?`
- Expected behavior:
  - Answer appears within 15-80 seconds
  - Citations are numbered (e.g., [1], [2], [3])
  - Paper titles are displayed below answer
  - Agent steps show tool selections (e.g., "keyword", "vector", "graph")
- Verify:
  - ✅ Answer text renders correctly
  - ✅ Citations are clickable/highlighted
  - ✅ No JavaScript errors in console
  - ✅ Agent steps section shows search queries

**Test Question 2: Multi-hop Query**
- Question: `What methods are evaluated on ImageNet?`
- Expected behavior:
  - May trigger multiple agent steps (decomposition)
  - Shows reasoning steps in agent timeline
  - Citations from multiple passages
- Verify:
  - ✅ Multiple agent steps visible
  - ✅ Different search queries shown
  - ✅ Citations link to correct passages

**Test Question 3: Abstention Case**
- Question: `What is the price of Bitcoin today?`
- Expected behavior:
  - Agent should abstain (out of domain)
  - Answer may be empty or state "insufficient evidence"
  - Fewer or no citations
- Verify:
  - ✅ Abstention is handled gracefully
  - ✅ No error messages displayed
  - ✅ UI remains functional for next query

#### 4. Performance Verification

Monitor timing for typical queries:
- **BM25-only retrieval:** ~14 seconds
- **Agent with graph retrieval:** ~77 seconds (first query may be slower due to cache building)
- **Health check:** <1 second

#### 5. Citation Display Test

For any query with citations:
- ✅ Citation IDs are sequential [1], [2], [3], etc.
- ✅ Paper titles are displayed below citations
- ✅ Hovering over citations shows passage context (if implemented)
- ✅ Citations match the passages used in the answer

#### 6. Agent Steps Display Test

Verify agent reasoning is visible:
- ✅ Each step shows:
  - Tool name (keyword, vector, graph)
  - Query text
  - Number of results retrieved
- ✅ Steps are displayed in chronological order
- ✅ Final answer step shows synthesis

### Expected Behavior Summary

- **Response time:** 15-80 seconds depending on agent complexity
- **Citations:** Numbered and linked to passages
- **Agent steps:** Tool selections and queries visible
- **Abstention:** Handled gracefully without errors
- **Memory usage:** ~8GB RAM for Qwen3 8B model

### Known Limitations

- **First query slow:** Embedding cache building may take extra time (~30s)
- **Large models:** Qwen 8B requires ~8GB RAM; consider smaller models if memory-constrained
- **Agent vs BM25:** Agent queries take ~77s vs BM25-only ~14s
- **No authentication:** API is local-only, no TLS or cross-origin support
- **Single user:** No concurrent request handling optimizations

### Troubleshooting UI Issues

**Page doesn't load:**
- Verify API is running: check terminal for uvicorn logs
- Check URL is exactly `http://127.0.0.1:8000/` (not localhost)
- Clear browser cache and reload

**Questions hang/timeout:**
- Check Ollama is running: `curl http://127.0.0.1:11434/api/tags`
- Verify models are loaded: `ollama list`
- Check API logs for errors
- Ensure data files exist in `data/processed/`

**JavaScript errors in console:**
- Check browser compatibility (requires modern browser with ES6 support)
- Verify `ui/index.html` is being served correctly
- Check network tab for failed requests

**No citations displayed:**
- Normal for abstention cases
- For domain questions, verify graph data exists
- Check API response in browser network tab

**Agent steps not showing:**
- Verify API is returning `steps` array in JSON response
- Check browser console for rendering errors
- Ensure agent mode is enabled (not BM25-only mode)

## Troubleshooting

### Ollama Connection Errors

```
Connection refused at http://127.0.0.1:11434
```

**Solution:** Ensure Ollama server is running (`ollama serve`) and accessible at the default port.

### Missing Data Files

```
FileNotFoundError: [Errno 2] No such file or directory: 'data/processed/domain_inventory_passages_v1.0.jsonl'
```

**Solution:** Run the data ingestion pipeline or download pre-processed data (see repository README).

### Import Errors

```
ModuleNotFoundError: No module named 'agentic_graphrag'
```

**Solution:** Install the package in editable mode: `pip install -e .`

### Model Not Found

```
Error: model 'qwen2.5:14b' not found
```

**Solution:** Pull the model with `ollama pull qwen2.5:14b`

## Configuration

The system uses `configs/default.toml` for configuration. Key settings:

- **Models:** LLM model names for extraction, planning, and answering
- **Retrieval:** BM25 parameters (k1, b), dense model settings, graph expansion parameters
- **Agent:** Maximum steps, tool top-k, context window

Edit this file to customize behavior.

## Next Steps

- **Read the Implementation Roadmap:** `docs/IMPLEMENTATION_ROADMAP.md`
- **Explore the codebase:** Start with `agent/run_agent.py` and `retrieval/`
- **Run evaluations:** See `eval/` directory for evaluation scripts
- **Review results:** Check `data/processed/` and `eval/results/` for outputs

## File Locations (Absolute Paths on This System)

- Repository root: `c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag`
- Config: `c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag\configs\default.toml`
- Tests: `c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag\tests\`
- Source code: `c:\Users\Vaishnavi\Desktop\Agentic-Graphrag\Agentic-Graphrag\src\agentic_graphrag\`

## Support

For issues, please check:
1. This quickstart guide
2. `docs/IMPLEMENTATION_ROADMAP.md` for detailed architecture
3. Repository README.md
4. Test files in `tests/` for usage examples
