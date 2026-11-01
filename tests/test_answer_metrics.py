"""Tests for answer and citation metrics."""

from __future__ import annotations

from typing import Any

import pytest

from eval.answer_metrics import (
    citation_metrics,
    exact_match,
    normalize_answer,
    token_f1,
)


def test_normalize_answer_basic() -> None:
    """Test basic answer normalization."""
    assert normalize_answer("Hello World") == "hello world"
    assert normalize_answer("HELLO WORLD") == "hello world"


def test_normalize_answer_punctuation() -> None:
    """Test that punctuation is removed."""
    assert normalize_answer("Hello, World!") == "hello world"
    assert normalize_answer("What's up?") == "whats up"
    assert normalize_answer("test.example@email.com") == "testexampleemailcom"


def test_normalize_answer_articles() -> None:
    """Test that articles are removed."""
    assert normalize_answer("the cat") == "cat"
    assert normalize_answer("a dog") == "dog"
    assert normalize_answer("an apple") == "apple"
    assert normalize_answer("The quick brown fox") == "quick brown fox"


def test_normalize_answer_whitespace() -> None:
    """Test that extra whitespace is normalized."""
    assert normalize_answer("  hello   world  ") == "hello world"
    assert normalize_answer("tab\tseparated") == "tab separated"


def test_normalize_answer_empty() -> None:
    """Test normalization of empty string."""
    assert normalize_answer("") == ""
    assert normalize_answer("   ") == ""


def test_normalize_answer_only_articles() -> None:
    """Test normalization when only articles remain."""
    assert normalize_answer("the a an") == ""


def test_exact_match_identical() -> None:
    """Test exact match with identical strings."""
    assert exact_match("Paris", ["Paris"]) == 1.0
    assert exact_match("42", ["42"]) == 1.0


def test_exact_match_case_insensitive() -> None:
    """Test that exact match is case-insensitive."""
    assert exact_match("Paris", ["paris"]) == 1.0
    assert exact_match("PARIS", ["paris"]) == 1.0


def test_exact_match_punctuation() -> None:
    """Test that exact match ignores punctuation."""
    assert exact_match("Hello!", ["Hello"]) == 1.0
    assert exact_match("Paris, France", ["Paris France"]) == 1.0


def test_exact_match_articles() -> None:
    """Test that exact match ignores articles."""
    assert exact_match("the cat", ["cat"]) == 1.0
    assert exact_match("a dog", ["dog"]) == 1.0


def test_exact_match_no_match() -> None:
    """Test exact match when no match exists."""
    assert exact_match("Paris", ["London"]) == 0.0
    assert exact_match("42", ["43"]) == 0.0


def test_exact_match_multiple_gold() -> None:
    """Test exact match with multiple gold answers."""
    assert exact_match("Paris", ["London", "Paris", "Berlin"]) == 1.0
    assert exact_match("London", ["Paris", "Berlin"]) == 0.0


def test_exact_match_empty() -> None:
    """Test exact match with empty strings."""
    assert exact_match("", [""]) == 1.0
    assert exact_match("something", [""]) == 0.0
    assert exact_match("", ["something"]) == 0.0


def test_token_f1_identical() -> None:
    """Test token F1 with identical strings."""
    assert token_f1("Paris", ["Paris"]) == 1.0


def test_token_f1_no_overlap() -> None:
    """Test token F1 with no overlap."""
    assert token_f1("Paris", ["London"]) == 0.0


def test_token_f1_partial_overlap() -> None:
    """Test token F1 with partial overlap."""
    # Prediction: "Paris France", Gold: "Paris"
    # Overlap: 1 token (Paris)
    # Precision: 1/2, Recall: 1/1, F1: 2 * (1/2 * 1) / (1/2 + 1) = 2/3
    score = token_f1("Paris France", ["Paris"])
    assert abs(score - 2/3) < 1e-6


def test_token_f1_case_insensitive() -> None:
    """Test that token F1 is case-insensitive."""
    assert token_f1("Paris", ["paris"]) == 1.0
    assert token_f1("PARIS FRANCE", ["paris france"]) == 1.0


def test_token_f1_punctuation() -> None:
    """Test that token F1 ignores punctuation."""
    assert token_f1("Paris!", ["Paris"]) == 1.0
    assert token_f1("Paris, France", ["Paris France"]) == 1.0


def test_token_f1_multiple_gold() -> None:
    """Test token F1 with multiple gold answers (takes max)."""
    score1 = token_f1("Paris", ["London"])
    score2 = token_f1("Paris", ["London", "Paris"])
    
    assert score1 == 0.0
    assert score2 == 1.0


def test_token_f1_empty() -> None:
    """Test token F1 with empty strings."""
    assert token_f1("", [""]) == 1.0
    assert token_f1("something", [""]) == 0.0
    assert token_f1("", ["something"]) == 0.0


def test_token_f1_duplicate_tokens() -> None:
    """Test token F1 with duplicate tokens."""
    # Prediction: "the the cat", Gold: "the cat"
    # After normalization: "cat" vs "cat"
    assert token_f1("the the cat", ["the cat"]) == 1.0


def test_citation_metrics_valid() -> None:
    """Test citation metrics with valid citations."""
    result = citation_metrics(["passage_1", "passage_2"], ["passage_1", "passage_2", "passage_3"])
    
    assert result["citation_ids"] == ["passage_1", "passage_2"]
    assert result["citation_valid"] is True
    assert result["valid_citation_fraction"] == 1.0
    assert result["unsupported_citation_ids"] == []


def test_citation_metrics_invalid() -> None:
    """Test citation metrics with invalid citations."""
    result = citation_metrics(["passage_1", "passage_99"], ["passage_1", "passage_2"])
    
    assert result["citation_ids"] == ["passage_1", "passage_99"]
    assert result["citation_valid"] is False
    assert result["valid_citation_fraction"] == 0.5
    assert result["unsupported_citation_ids"] == ["passage_99"]


def test_citation_metrics_no_citations() -> None:
    """Test citation metrics with no citations."""
    result = citation_metrics([], ["passage_1", "passage_2"])
    
    assert result["citation_ids"] == []
    assert result["citation_valid"] is False
    assert result["valid_citation_fraction"] == 0.0
    assert result["unsupported_citation_ids"] == []


def test_citation_metrics_abstained() -> None:
    """Test citation metrics when abstained."""
    result = citation_metrics([], ["passage_1", "passage_2"], abstained=True)
    
    assert result["citation_ids"] == []
    assert result["citation_valid"] is True
    assert result["valid_citation_fraction"] == 1.0
    assert result["unsupported_citation_ids"] == []


def test_citation_metrics_abstained_with_citations() -> None:
    """Test citation metrics when abstained but has citations (invalid)."""
    result = citation_metrics(["passage_1"], ["passage_1"], abstained=True)
    
    assert result["citation_valid"] is False  # Should not cite when abstaining


def test_citation_metrics_all_invalid() -> None:
    """Test citation metrics when all citations are invalid."""
    result = citation_metrics(["passage_99", "passage_100"], ["passage_1", "passage_2"])
    
    assert result["citation_valid"] is False
    assert result["valid_citation_fraction"] == 0.0
    assert result["unsupported_citation_ids"] == ["passage_99", "passage_100"]


def test_citation_metrics_empty_retrieved() -> None:
    """Test citation metrics with no retrieved passages."""
    result = citation_metrics(["passage_1"], [])
    
    assert result["citation_valid"] is False
    assert result["valid_citation_fraction"] == 0.0
    assert result["unsupported_citation_ids"] == ["passage_1"]


def test_token_f1_articles() -> None:
    """Test that token F1 ignores articles."""
    # Both normalize to "cat"
    assert token_f1("the cat", ["a cat"]) == 1.0
    assert token_f1("a big cat", ["the big cat"]) == 1.0


def test_normalize_answer_preserves_alphanumeric() -> None:
    """Test that alphanumeric content is preserved."""
    assert "bert" in normalize_answer("BERT")
    assert "gpt3" in normalize_answer("GPT-3")
    assert "42" in normalize_answer("answer is 42")
