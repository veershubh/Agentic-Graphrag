"""Small stdlib-only client for schema-constrained local Ollama inference."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, response: Any, code: int, message: str, headers: Any, new_url: str) -> None:
        return None


@dataclass(frozen=True)
class LocalUsage:
    input_tokens: int
    output_tokens: int
    total_duration_ns: int
    load_duration_ns: int
    prompt_duration_ns: int
    generation_duration_ns: int


@dataclass(frozen=True)
class LocalResponse:
    output_text: str
    id: str
    model: str
    usage: LocalUsage
    done_reason: str


class LocalOllamaClient:
    """Send inference only to a loopback Ollama server; model pulls are separate."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout_seconds: int = 900, keep_alive: str = "10m"):
        parsed = urlparse(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("LocalOllamaClient accepts only an HTTP loopback URL")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        self.endpoint = base_url.rstrip("/") + "/api/chat"
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive

    def structured_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float = 0.0,
        max_output_tokens: int = 700,
        think: bool = False,
    ) -> LocalResponse:
        if not model.strip() or max_output_tokens < 1:
            raise ValueError("model and max_output_tokens must be set")
        payload = {
            "model": model,
            "messages": [
                {**message, "role": "system" if message.get("role") == "developer" else message.get("role", "user")}
                for message in messages
            ],
            "format": schema,
            "think": think,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_predict": max_output_tokens},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            # Do not let process-wide proxy settings route local passage text elsewhere.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
            with opener.open(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Local Ollama returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                "Could not reach local Ollama. Start the Ollama service and pull the configured model first."
            ) from error

        message = data.get("message", {})
        output_text = str(message.get("content", ""))
        if not output_text:
            raise RuntimeError(f"Local Ollama returned empty output (done_reason={data.get('done_reason')})")
        usage = LocalUsage(
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
            total_duration_ns=int(data.get("total_duration", 0)),
            load_duration_ns=int(data.get("load_duration", 0)),
            prompt_duration_ns=int(data.get("prompt_eval_duration", 0)),
            generation_duration_ns=int(data.get("eval_duration", 0)),
        )
        return LocalResponse(
            output_text=output_text,
            id="local_" + uuid.uuid4().hex,
            model=str(data.get("model", model)),
            usage=usage,
            done_reason=str(data.get("done_reason", "unknown")),
        )
