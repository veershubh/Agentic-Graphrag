"""Shared pytest fixtures for Agentic GraphRAG tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Add repository root to sys.path so tests can import from graph/, retrieval/, eval/
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


@pytest.fixture
def temp_jsonl_file(tmp_path: Path) -> Path:
    """Create a temporary JSONL file path."""
    return tmp_path / "test.jsonl"


@pytest.fixture
def sample_jsonl_data() -> list[dict[str, Any]]:
    """Sample JSONL data for testing."""
    return [
        {"id": "1", "text": "First record"},
        {"id": "2", "text": "Second record"},
        {"id": "3", "text": "Third record"},
    ]


@pytest.fixture
def sample_passages() -> list[dict[str, Any]]:
    """Sample passages for retrieval testing."""
    return [
        {"id": "passage_1", "text": "The quick brown fox jumps over the lazy dog"},
        {"id": "passage_2", "text": "Machine learning is a subset of artificial intelligence"},
        {"id": "passage_3", "text": "Natural language processing deals with text understanding"},
        {"id": "passage_4", "text": "Deep learning uses neural networks with multiple layers"},
        {"id": "passage_5", "text": "The fox is quick and brown in color"},
    ]


@pytest.fixture
def sample_graph_nodes() -> list[dict[str, Any]]:
    """Sample graph nodes for testing."""
    return [
        {
            "id": "entity_1",
            "kind": "Method",
            "name": "BERT",
            "aliases": ["Bidirectional Encoder Representations"],
            "source_chunk_ids": ["chunk_1"],
            "paper_ids": ["paper_1"],
        },
        {
            "id": "entity_2",
            "kind": "Dataset",
            "name": "ImageNet",
            "aliases": [],
            "source_chunk_ids": ["chunk_2"],
            "paper_ids": ["paper_2"],
        },
        {
            "id": "entity_3",
            "kind": "Task",
            "name": "Image Classification",
            "aliases": [],
            "source_chunk_ids": ["chunk_2"],
            "paper_ids": ["paper_2"],
        },
    ]


@pytest.fixture
def sample_graph_edges() -> list[dict[str, Any]]:
    """Sample graph edges for testing."""
    return [
        {
            "id": "edge_1",
            "subject_id": "entity_1",
            "predicate": "EVALUATES_ON",
            "object_id": "entity_2",
            "evidence": [{"source_chunk_id": "chunk_1", "paper_id": "paper_1", "confidence": 0.95}],
        },
        {
            "id": "edge_2",
            "subject_id": "entity_2",
            "predicate": "USES",
            "object_id": "entity_3",
            "evidence": [{"source_chunk_id": "chunk_2", "paper_id": "paper_2", "confidence": 0.90}],
        },
    ]
