"""Shared I/O utilities for reading/writing JSONL and computing file hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dictionaries."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a list of dictionaries to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
