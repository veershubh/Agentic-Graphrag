"""Loopback-only FastAPI wrapper around the local agent CLI."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.request
import uuid
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPOSITORY_ROOT / "configs" / "default.toml"
CONFIG = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
LOCAL_CONFIG = CONFIG.get("local_llm", {})
MAX_CONCURRENCY = max(1, int(os.getenv("GRAPHRAG_MAX_CONCURRENCY", "1")))
REQUESTS_PER_MINUTE = max(1, int(os.getenv("GRAPHRAG_REQUESTS_PER_MINUTE", "5")))
REQUEST_TIMEOUT_SECONDS = max(30, int(os.getenv("GRAPHRAG_REQUEST_TIMEOUT_SECONDS", "900")))
OLLAMA_BASE_URL = str(LOCAL_CONFIG.get("base_url", "http://127.0.0.1:11434"))
ollama_url = urlparse(OLLAMA_BASE_URL)
if (
    ollama_url.scheme != "http"
    or ollama_url.hostname not in {"localhost", "127.0.0.1", "::1"}
    or ollama_url.username is not None
    or ollama_url.password is not None
    or ollama_url.path not in {"", "/"}
    or ollama_url.query
    or ollama_url.fragment
):
    raise RuntimeError("The local API only supports a loopback Ollama endpoint")
OLLAMA_TAGS_URL = OLLAMA_BASE_URL.rstrip("/") + "/api/tags"

app = FastAPI(title="Local Agentic GraphRAG", version="0.1.0")
request_slots = asyncio.Semaphore(MAX_CONCURRENCY)
rate_lock = asyncio.Lock()
request_timestamps: deque[float] = deque()


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


class Citation(BaseModel):
    passage_id: str
    title: str


class AgentStep(BaseModel):
    step: int
    action: str
    tool: str
    query: str
    result_ids: list[str]


class AskResponse(BaseModel):
    answer: str
    abstained: bool
    citation_valid: bool
    citations: list[Citation]
    steps: list[AgentStep]
    stop_reason: str
    latency_seconds: float
    estimated_model_api_cost_usd: float


def local_resources_ready() -> dict[str, Any]:
    resources = {
        "passages": REPOSITORY_ROOT / "data" / "processed" / "domain_inventory_passages_v1.0.jsonl",
        "graph_nodes": REPOSITORY_ROOT / "data" / "processed" / "domain_graph_nodes.jsonl",
        "graph_edges": REPOSITORY_ROOT / "data" / "processed" / "domain_graph_edges.jsonl",
    }
    files = {name: path.is_file() for name, path in resources.items()}
    ollama_ready = False
    installed_models: set[str] = set()
    try:
        request = urllib.request.Request(OLLAMA_TAGS_URL, method="GET")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            installed_models = {str(model.get("name", "")) for model in payload.get("models", [])}
            ollama_ready = response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        pass
    required_models = {
        "planner": str(CONFIG["models"]["planning"]),
        "answer": str(CONFIG["models"]["answer"]),
    }
    models = {role: name in installed_models for role, name in required_models.items()}
    return {
        "ready": all(files.values()) and ollama_ready and all(models.values()),
        "files": files,
        "ollama": ollama_ready,
        "models": models,
    }


async def apply_rate_limit() -> None:
    now = time.monotonic()
    async with rate_lock:
        while request_timestamps and now - request_timestamps[0] >= 60:
            request_timestamps.popleft()
        if len(request_timestamps) >= REQUESTS_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Local request limit reached; retry after one minute")
        request_timestamps.append(now)


@app.get("/healthz")
async def health() -> dict[str, Any]:
    return local_resources_ready()


@app.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest) -> AskResponse:
    await apply_rate_limit()
    readiness = local_resources_ready()
    if not readiness["ready"]:
        raise HTTPException(status_code=503, detail="Local corpus, graph, or Ollama runtime is not ready")

    run_directory = REPOSITORY_ROOT / "data" / "processed" / "api_runs"
    run_directory.mkdir(parents=True, exist_ok=True)
    output_path = run_directory / f"{uuid.uuid4().hex}.json"
    command = [
        sys.executable,
        str(REPOSITORY_ROOT / "agent" / "run_agent.py"),
        "--question",
        payload.question.strip(),
        "--output",
        str(output_path),
    ]
    started = time.perf_counter()
    process = None
    async with request_slots:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=REPOSITORY_ROOT,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(process.wait(), timeout=REQUEST_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as error:
            process.kill()
            await process.wait()
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=504, detail="Local research request exceeded its time limit") from error
        except asyncio.CancelledError:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            output_path.unlink(missing_ok=True)
            raise
        except OSError as error:
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail="Could not start the local agent process") from error

    if process.returncode != 0 or not output_path.is_file():
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail="The local agent could not complete this request")

    try:
        result = json.loads(output_path.read_text(encoding="utf-8"))
    finally:
        output_path.unlink(missing_ok=True)

    passage_titles = {
        str(item["id"]): str(item.get("title", "")) for item in result.get("retrieved", [])
    }
    citations = [
        Citation(passage_id=str(identifier), title=passage_titles.get(str(identifier), ""))
        for identifier in result.get("citation_ids", [])
    ]
    steps = [
        AgentStep(
            step=int(item["step"]),
            action=str(item["action"]),
            tool=str(item["tool"]),
            query=str(item["query"]),
            result_ids=[str(identifier) for identifier in item.get("result_ids", [])],
        )
        for item in result.get("steps", [])
    ]
    return AskResponse(
        answer=str(result.get("answer", "")),
        abstained=bool(result.get("abstained", True)),
        citation_valid=bool(result.get("citation_valid", False)),
        citations=citations,
        steps=steps,
        stop_reason=str(result.get("stop_reason", "unknown")),
        latency_seconds=float(time.perf_counter() - started),
        estimated_model_api_cost_usd=0.0,
    )
