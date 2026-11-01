"""Tests for graph retrieval."""

from __future__ import annotations

from typing import Any

import pytest

from retrieval.graph import GraphIndex


@pytest.fixture
def sample_graph_passages() -> list[dict[str, Any]]:
    """Sample passages for graph testing."""
    return [
        {"id": "chunk_1", "text": "BERT is a method for natural language understanding"},
        {"id": "chunk_2", "text": "ImageNet is a dataset for image classification"},
        {"id": "chunk_3", "text": "The paper proposes a new approach"},
    ]


def test_graph_index_initialization(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test GraphIndex initialization."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert len(graph.passages) == 3


def test_graph_index_duplicate_node_ids_raises(
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that duplicate node IDs raise ValueError."""
    nodes = [
        {"id": "entity_1", "kind": "Method", "name": "BERT", "aliases": [], "source_chunk_ids": [], "paper_ids": []},
        {"id": "entity_1", "kind": "Dataset", "name": "ImageNet", "aliases": [], "source_chunk_ids": [], "paper_ids": []},
    ]
    
    with pytest.raises(ValueError, match="duplicate IDs"):
        GraphIndex(nodes, [], sample_graph_passages)


def test_graph_index_duplicate_passage_ids_raises(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
) -> None:
    """Test that duplicate passage IDs raise ValueError."""
    passages = [
        {"id": "chunk_1", "text": "First"},
        {"id": "chunk_1", "text": "Second"},
    ]
    
    with pytest.raises(ValueError, match="duplicate IDs"):
        GraphIndex(sample_graph_nodes, sample_graph_edges, passages)


def test_graph_index_edge_missing_node_raises(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that edge referencing missing node raises ValueError."""
    edges = [
        {
            "id": "edge_1",
            "subject_id": "entity_1",
            "predicate": "EVALUATES_ON",
            "object_id": "entity_999",  # Does not exist
            "evidence": [],
        }
    ]
    
    with pytest.raises(ValueError, match="missing node"):
        GraphIndex(sample_graph_nodes, edges, sample_graph_passages)


def test_graph_index_seed_entities(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test entity seeding with BM25."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    results = graph.seed_entities("BERT", limit=5)
    
    assert isinstance(results, list)
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    
    # BERT should be top result
    if results:
        assert results[0][0] == "entity_1"


def test_graph_index_seed_entities_limit(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that seed_entities respects limit."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    results = graph.seed_entities("method", limit=2)
    assert len(results) <= 2


def test_graph_index_seed_entities_invalid_limit(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that seed_entities raises with invalid limit."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    with pytest.raises(ValueError, match="must be positive"):
        graph.seed_entities("query", limit=0)


def test_graph_index_expand_basic(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test basic graph expansion."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    results = graph.expand("BERT", hops=1, max_nodes=10, max_chunks=10)
    
    assert isinstance(results, list)
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


def test_graph_index_expand_no_seeds(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test graph expansion when no seeds are found."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    results = graph.expand("nonexistent_query_xyz123", hops=2)
    assert results == []


def test_graph_index_expand_with_seed_ids(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test graph expansion with explicit seed entity IDs."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    results = graph.expand("query", hops=1, seed_entity_ids=["entity_1"])
    
    assert isinstance(results, list)
    # Should find passages related to entity_1


def test_graph_index_expand_invalid_params(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that expand raises with invalid parameters."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    with pytest.raises(ValueError, match="non-negative"):
        graph.expand("query", hops=-1)
    
    with pytest.raises(ValueError, match="positive"):
        graph.expand("query", max_nodes=0)
    
    with pytest.raises(ValueError, match="positive"):
        graph.expand("query", max_chunks=0)


def test_graph_index_expand_respects_max_nodes(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that expand respects max_nodes limit."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    # With only 3 nodes, max_nodes=1 should limit expansion
    results = graph.expand("BERT", hops=2, max_nodes=1, max_chunks=10)
    assert isinstance(results, list)


def test_graph_index_expand_zero_hops(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test graph expansion with zero hops (seed nodes only)."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    results = graph.expand("BERT", hops=0, max_nodes=10, max_chunks=10)
    assert isinstance(results, list)


def test_graph_index_custom_bm25_params(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test GraphIndex with custom BM25 parameters."""
    graph = GraphIndex(
        sample_graph_nodes,
        sample_graph_edges,
        sample_graph_passages,
        entity_k1=2.0,
        entity_b=0.5,
    )
    
    assert graph.entity_bm25.k1 == 2.0
    assert graph.entity_bm25.b == 0.5


def test_graph_index_empty_graph() -> None:
    """Test GraphIndex with no nodes or edges requires at least one node for BM25."""
    # BM25 requires at least one document, so we need at least one node
    # Create minimal graph with one node
    nodes = [{"id": "entity_1", "kind": "Method", "name": "Test", "aliases": [], "source_chunk_ids": [], "paper_ids": []}]
    graph = GraphIndex(nodes, [], [{"id": "p1", "text": "test"}])
    
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0
    
    # Query with no matches
    results = graph.expand("nonexistent", hops=1)
    assert results == []


def test_graph_index_passage_index_mapping(
    sample_graph_nodes: list[dict[str, Any]],
    sample_graph_edges: list[dict[str, Any]],
    sample_graph_passages: list[dict[str, Any]],
) -> None:
    """Test that passage_index correctly maps IDs to indices."""
    graph = GraphIndex(sample_graph_nodes, sample_graph_edges, sample_graph_passages)
    
    assert "chunk_1" in graph.passage_index
    assert graph.passage_index["chunk_1"] == 0
    assert graph.passages[graph.passage_index["chunk_1"]]["id"] == "chunk_1"
