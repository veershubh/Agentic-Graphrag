# Local research UI

The static page in `index.html` is served from the same FastAPI origin at `/`. It submits questions to `/ask` and displays the answer or abstention, citation IDs and paper titles, latency, and the planner's keyword/vector/graph search steps. It has no JavaScript, stylesheet, font, or analytics dependencies outside the repository.

Start the API as documented in `../api/README.md`, keeping Uvicorn bound to `127.0.0.1`, then open <http://127.0.0.1:8000/>.

**⚠️ Browser testing checklist available in [`docs/QUICKSTART.md`](../docs/QUICKSTART.md#browser-testing-checklist).** Manual verification required by user with Ollama running locally. The checklist includes health checks, test questions, citation verification, and agent step validation.

A hosted demo, authentication, TLS, and cross-origin support are not configured.
