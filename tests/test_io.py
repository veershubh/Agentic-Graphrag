"""Tests for shared I/O utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentic_graphrag.io import read_jsonl, sha256_file, write_jsonl


def test_write_jsonl_creates_file(temp_jsonl_file: Path, sample_jsonl_data: list[dict[str, Any]]) -> None:
    """Test that write_jsonl creates a file with correct content."""
    write_jsonl(temp_jsonl_file, sample_jsonl_data)
    assert temp_jsonl_file.exists()
    
    # Verify content
    content = temp_jsonl_file.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    assert len(lines) == len(sample_jsonl_data)
    
    for i, line in enumerate(lines):
        parsed = json.loads(line)
        assert parsed == sample_jsonl_data[i]


def test_write_jsonl_creates_parent_directories(tmp_path: Path, sample_jsonl_data: list[dict[str, Any]]) -> None:
    """Test that write_jsonl creates parent directories if they don't exist."""
    nested_path = tmp_path / "nested" / "dir" / "test.jsonl"
    write_jsonl(nested_path, sample_jsonl_data)
    assert nested_path.exists()
    assert nested_path.parent.exists()


def test_read_jsonl_reads_file(temp_jsonl_file: Path, sample_jsonl_data: list[dict[str, Any]]) -> None:
    """Test that read_jsonl correctly reads a JSONL file."""
    write_jsonl(temp_jsonl_file, sample_jsonl_data)
    result = read_jsonl(temp_jsonl_file)
    assert result == sample_jsonl_data


def test_read_jsonl_skips_empty_lines(temp_jsonl_file: Path) -> None:
    """Test that read_jsonl skips empty lines."""
    content = '{"id": "1"}\n\n{"id": "2"}\n  \n{"id": "3"}\n'
    temp_jsonl_file.write_text(content, encoding="utf-8")
    
    result = read_jsonl(temp_jsonl_file)
    assert len(result) == 3
    assert result[0]["id"] == "1"
    assert result[1]["id"] == "2"
    assert result[2]["id"] == "3"


def test_read_jsonl_handles_unicode(temp_jsonl_file: Path) -> None:
    """Test that read_jsonl correctly handles Unicode characters."""
    data = [{"text": "Hello 世界"}, {"emoji": "🚀"}]
    write_jsonl(temp_jsonl_file, data)
    result = read_jsonl(temp_jsonl_file)
    assert result == data


def test_read_write_jsonl_roundtrip(temp_jsonl_file: Path, sample_jsonl_data: list[dict[str, Any]]) -> None:
    """Test that data survives a write-read roundtrip."""
    write_jsonl(temp_jsonl_file, sample_jsonl_data)
    result = read_jsonl(temp_jsonl_file)
    assert result == sample_jsonl_data


def test_read_jsonl_empty_file(temp_jsonl_file: Path) -> None:
    """Test that read_jsonl returns empty list for empty file."""
    temp_jsonl_file.write_text("", encoding="utf-8")
    result = read_jsonl(temp_jsonl_file)
    assert result == []


def test_sha256_file_computes_hash(temp_jsonl_file: Path) -> None:
    """Test that sha256_file computes correct hash."""
    content = "test content"
    temp_jsonl_file.write_text(content, encoding="utf-8")
    
    result = sha256_file(temp_jsonl_file)
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 produces 64 hex characters
    
    # Verify hash is consistent
    result2 = sha256_file(temp_jsonl_file)
    assert result == result2


def test_sha256_file_different_content(tmp_path: Path) -> None:
    """Test that different files produce different hashes."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    
    file1.write_text("content 1", encoding="utf-8")
    file2.write_text("content 2", encoding="utf-8")
    
    hash1 = sha256_file(file1)
    hash2 = sha256_file(file2)
    
    assert hash1 != hash2


def test_write_jsonl_empty_list(temp_jsonl_file: Path) -> None:
    """Test that write_jsonl handles empty list."""
    write_jsonl(temp_jsonl_file, [])
    assert temp_jsonl_file.exists()
    
    result = read_jsonl(temp_jsonl_file)
    assert result == []
