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

```bash
# Install API dependencies
pip install -e ".[api]"

# Start the API server
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Open your browser to [http://127.0.0.1:8000/](http://127.0.0.1:8000/) to access the web UI.

**Test in browser:**
1. Enter a question (e.g., "What is BERT?")
2. Click "Ask"
3. Wait for response (may take 30-60 seconds)
4. Verify answer and citations are displayed

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
