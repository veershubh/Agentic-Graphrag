"""Tests for graph ontology functions."""

from __future__ import annotations

import pytest

from graph.ontology import (
    ALLOWED_ENDPOINTS,
    ENTITY_KINDS,
    PREDICATES,
    normalize_name,
    stable_entity_id,
)


def test_normalize_name_basic() -> None:
    """Test basic name normalization."""
    assert normalize_name("BERT") == "bert"
    assert normalize_name("GPT-3") == "gpt 3"
    assert normalize_name("ResNet-50") == "resnet 50"


def test_normalize_name_whitespace() -> None:
    """Test that multiple whitespace is normalized."""
    assert normalize_name("  hello   world  ") == "hello world"
    assert normalize_name("tab\tseparated") == "tab separated"
    assert normalize_name("new\nline") == "new line"


def test_normalize_name_punctuation() -> None:
    """Test that punctuation is removed."""
    assert normalize_name("Hello, World!") == "hello world"
    assert normalize_name("one-two-three") == "one two three"
    assert normalize_name("test@example.com") == "test example com"


def test_normalize_name_unicode() -> None:
    """Test Unicode handling in normalization."""
    assert normalize_name("café") == "café"
    assert normalize_name("naïve") == "naïve"


def test_normalize_name_empty() -> None:
    """Test normalization of empty or whitespace-only strings."""
    assert normalize_name("") == ""
    assert normalize_name("   ") == ""
    assert normalize_name("\t\n") == ""


def test_normalize_name_numbers() -> None:
    """Test normalization with numbers."""
    assert normalize_name("GPT-3.5") == "gpt 3 5"
    assert normalize_name("Version 2.0") == "version 2 0"


def test_stable_entity_id_valid() -> None:
    """Test stable entity ID generation for valid inputs."""
    entity_id = stable_entity_id("Method", "BERT")
    
    # Should return consistent format
    assert entity_id.startswith("method_")
    assert len(entity_id) == 27  # "method_" (7) + 20 hex chars
    
    # Should be consistent across calls
    entity_id2 = stable_entity_id("Method", "BERT")
    assert entity_id == entity_id2


def test_stable_entity_id_case_insensitive() -> None:
    """Test that entity IDs are case-insensitive."""
    id1 = stable_entity_id("Method", "BERT")
    id2 = stable_entity_id("Method", "bert")
    id3 = stable_entity_id("Method", "Bert")
    
    assert id1 == id2 == id3


def test_stable_entity_id_different_kinds() -> None:
    """Test that different kinds produce different IDs."""
    id_method = stable_entity_id("Method", "BERT")
    id_paper = stable_entity_id("Paper", "BERT")
    
    assert id_method != id_paper
    assert id_method.startswith("method_")
    assert id_paper.startswith("paper_")


def test_stable_entity_id_different_names() -> None:
    """Test that different names produce different IDs."""
    id1 = stable_entity_id("Method", "BERT")
    id2 = stable_entity_id("Method", "GPT")
    
    assert id1 != id2


def test_stable_entity_id_normalized_equivalence() -> None:
    """Test that names that normalize to same value produce same ID."""
    id1 = stable_entity_id("Method", "GPT-3")
    id2 = stable_entity_id("Method", "GPT 3")
    id3 = stable_entity_id("Method", "gpt  3")
    
    assert id1 == id2 == id3


def test_stable_entity_id_invalid_kind() -> None:
    """Test that invalid entity kind raises ValueError."""
    with pytest.raises(ValueError, match="Invalid graph entity"):
        stable_entity_id("InvalidKind", "BERT")


def test_stable_entity_id_empty_name() -> None:
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="Invalid graph entity"):
        stable_entity_id("Method", "")


def test_stable_entity_id_whitespace_only_name() -> None:
    """Test that whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="Invalid graph entity"):
        stable_entity_id("Method", "   ")


def test_entity_kinds_constant() -> None:
    """Test that ENTITY_KINDS contains expected values."""
    assert "Paper" in ENTITY_KINDS
    assert "Method" in ENTITY_KINDS
    assert "Dataset" in ENTITY_KINDS
    assert "Metric" in ENTITY_KINDS
    assert "Task" in ENTITY_KINDS
    assert len(ENTITY_KINDS) == 5


def test_predicates_constant() -> None:
    """Test that PREDICATES contains expected values."""
    assert "PROPOSES" in PREDICATES
    assert "EVALUATES_ON" in PREDICATES
    assert "USES" in PREDICATES
    assert "OUTPERFORMS" in PREDICATES
    assert "CITES" in PREDICATES
    assert len(PREDICATES) == 5


def test_allowed_endpoints_structure() -> None:
    """Test that ALLOWED_ENDPOINTS has correct structure."""
    for predicate in PREDICATES:
        assert predicate in ALLOWED_ENDPOINTS
        subjects, objects = ALLOWED_ENDPOINTS[predicate]
        assert isinstance(subjects, set)
        assert isinstance(objects, set)
        # All endpoint kinds should be valid entity kinds
        assert all(kind in ENTITY_KINDS for kind in subjects)
        assert all(kind in ENTITY_KINDS for kind in objects)


def test_allowed_endpoints_proposes() -> None:
    """Test PROPOSES predicate endpoints."""
    subjects, objects = ALLOWED_ENDPOINTS["PROPOSES"]
    assert subjects == {"Paper"}
    assert objects == {"Method"}


def test_allowed_endpoints_evaluates_on() -> None:
    """Test EVALUATES_ON predicate endpoints."""
    subjects, objects = ALLOWED_ENDPOINTS["EVALUATES_ON"]
    assert "Paper" in subjects
    assert "Method" in subjects
    assert "Dataset" in objects
    assert "Task" in objects
    assert "Metric" in objects


def test_allowed_endpoints_uses() -> None:
    """Test USES predicate endpoints."""
    subjects, objects = ALLOWED_ENDPOINTS["USES"]
    assert "Paper" in subjects
    assert "Method" in subjects
    assert "Method" in objects
    assert "Dataset" in objects


def test_allowed_endpoints_outperforms() -> None:
    """Test OUTPERFORMS predicate endpoints."""
    subjects, objects = ALLOWED_ENDPOINTS["OUTPERFORMS"]
    assert subjects == {"Method"}
    assert objects == {"Method"}


def test_allowed_endpoints_cites() -> None:
    """Test CITES predicate endpoints."""
    subjects, objects = ALLOWED_ENDPOINTS["CITES"]
    assert subjects == {"Paper"}
    assert objects == {"Paper"}


def test_normalize_name_idempotent() -> None:
    """Test that normalizing twice gives same result."""
    original = "Hello, World! 123"
    normalized_once = normalize_name(original)
    normalized_twice = normalize_name(normalized_once)
    
    assert normalized_once == normalized_twice
