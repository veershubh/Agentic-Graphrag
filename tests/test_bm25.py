"""Tests for BM25 retrieval."""

from __future__ import annotations

from typing import Any

import pytest

from retrieval.bm25 import BM25, SearchResult, tokenize


def test_tokenize_basic() -> None:
    """Test basic tokenization."""
    result = tokenize("Hello World")
    assert result == ["hello", "world"]


def test_tokenize_unicode() -> None:
    """Test tokenization with Unicode characters."""
    result = tokenize("café résumé naïve")
    assert result == ["café", "résumé", "naïve"]


def test_tokenize_punctuation() -> None:
    """Test that punctuation is removed."""
    result = tokenize("Hello, World! How are you?")
    assert result == ["hello", "world", "how", "are", "you"]


def test_tokenize_numbers() -> None:
    """Test tokenization with numbers."""
    result = tokenize("Python 3.11 is here")
    assert result == ["python", "3", "11", "is", "here"]


def test_tokenize_empty() -> None:
    """Test tokenization of empty string."""
    result = tokenize("")
    assert result == []


def test_tokenize_casefold() -> None:
    """Test that tokenization is case-insensitive."""
    result1 = tokenize("HELLO")
    result2 = tokenize("hello")
    result3 = tokenize("Hello")
    assert result1 == result2 == result3


def test_bm25_initialization(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 initializes correctly."""
    bm25 = BM25(sample_passages, k1=1.5, b=0.75)
    assert bm25.documents == sample_passages
    assert bm25.k1 == 1.5
    assert bm25.b == 0.75
    assert len(bm25.tokens) == len(sample_passages)


def test_bm25_empty_documents_raises() -> None:
    """Test that BM25 raises ValueError with empty document list."""
    with pytest.raises(ValueError, match="at least one document"):
        BM25([])


def test_bm25_invalid_k1_raises(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 raises ValueError with invalid k1."""
    with pytest.raises(ValueError, match="k1 > 0"):
        BM25(sample_passages, k1=0)
    
    with pytest.raises(ValueError, match="k1 > 0"):
        BM25(sample_passages, k1=-1)


def test_bm25_invalid_b_raises(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 raises ValueError with invalid b."""
    with pytest.raises(ValueError, match="0 <= b <= 1"):
        BM25(sample_passages, b=-0.1)
    
    with pytest.raises(ValueError, match="0 <= b <= 1"):
        BM25(sample_passages, b=1.1)


def test_bm25_search_returns_results(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 search returns results."""
    bm25 = BM25(sample_passages)
    results = bm25.search("fox", top_k=5)
    
    assert isinstance(results, list)
    assert all(isinstance(r, SearchResult) for r in results)
    assert len(results) <= 5


def test_bm25_search_relevance(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 returns relevant results."""
    bm25 = BM25(sample_passages)
    results = bm25.search("fox", top_k=3)
    
    # Both passages with "fox" should be in results
    result_ids = [r.document["id"] for r in results]
    assert "passage_1" in result_ids  # "The quick brown fox..."
    assert "passage_5" in result_ids  # "The fox is quick..."


def test_bm25_search_scores_sorted(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 results are sorted by score."""
    bm25 = BM25(sample_passages)
    results = bm25.search("machine learning neural", top_k=5)
    
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_bm25_search_case_insensitive(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 search is case-insensitive."""
    bm25 = BM25(sample_passages)
    results1 = bm25.search("FOX", top_k=3)
    results2 = bm25.search("fox", top_k=3)
    results3 = bm25.search("Fox", top_k=3)
    
    ids1 = [r.document["id"] for r in results1]
    ids2 = [r.document["id"] for r in results2]
    ids3 = [r.document["id"] for r in results3]
    
    assert ids1 == ids2 == ids3


def test_bm25_search_no_matches(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 returns empty list when no matches."""
    bm25 = BM25(sample_passages)
    results = bm25.search("xyz123nonexistent", top_k=5)
    assert results == []


def test_bm25_search_respects_top_k(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 respects the top_k parameter."""
    bm25 = BM25(sample_passages)
    
    results_2 = bm25.search("the", top_k=2)
    assert len(results_2) <= 2
    
    results_3 = bm25.search("the", top_k=3)
    assert len(results_3) <= 3


def test_bm25_search_invalid_top_k(sample_passages: list[dict[str, Any]]) -> None:
    """Test that BM25 raises ValueError with invalid top_k."""
    bm25 = BM25(sample_passages)
    
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        bm25.search("fox", top_k=0)


def test_bm25_search_multiword_query(sample_passages: list[dict[str, Any]]) -> None:
    """Test BM25 with multi-word query."""
    bm25 = BM25(sample_passages)
    results = bm25.search("machine learning", top_k=3)
    
    # Passage 2 contains both "machine" and "learning"
    result_ids = [r.document["id"] for r in results]
    assert "passage_2" in result_ids
    assert results[0].document["id"] == "passage_2"  # Should be top result


def test_bm25_empty_query(sample_passages: list[dict[str, Any]]) -> None:
    """Test BM25 with empty query."""
    bm25 = BM25(sample_passages)
    results = bm25.search("", top_k=5)
    assert results == []


def test_bm25_single_document() -> None:
    """Test BM25 with single document."""
    docs = [{"id": "1", "text": "hello world"}]
    bm25 = BM25(docs)
    results = bm25.search("hello", top_k=1)
    
    assert len(results) == 1
    assert results[0].document["id"] == "1"
    assert results[0].score > 0


def test_bm25_document_with_title(sample_passages: list[dict[str, Any]]) -> None:
    """Test BM25 indexes both title and text fields."""
    docs = [
        {"id": "1", "title": "Machine Learning", "text": "Introduction to ML"},
        {"id": "2", "title": "Deep Learning", "text": "About neural networks"},
    ]
    bm25 = BM25(docs)
    
    # Search for term only in title
    results = bm25.search("machine", top_k=2)
    assert results[0].document["id"] == "1"


def test_search_result_dataclass() -> None:
    """Test SearchResult dataclass."""
    doc = {"id": "1", "text": "test"}
    result = SearchResult(document=doc, score=1.5)
    
    assert result.document == doc
    assert result.score == 1.5
    
    # Test frozen (immutability)
    with pytest.raises(Exception):  # FrozenInstanceError
        result.score = 2.0  # type: ignore
