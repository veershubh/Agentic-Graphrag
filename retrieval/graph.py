"""Bounded graph expansion over provenance-linked entity and passage records."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from retrieval.bm25 import BM25
from retrieval.fusion import reciprocal_rank_fusion


class GraphIndex:
    """In-memory entity graph with chunk provenance for local evaluation."""

    def __init__(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        passages: list[dict[str, Any]],
        *,
        entity_k1: float = 1.5,
        entity_b: float = 0.75,
    ):
        self.nodes = {str(node["id"]): node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("Graph nodes contain duplicate IDs")
        self.passages = passages
        self.passage_index = {str(passage["id"]): index for index, passage in enumerate(passages)}
        if len(self.passage_index) != len(passages):
            raise ValueError("Passages contain duplicate IDs")
        self.adjacency: dict[str, list[tuple[str, dict[str, Any], bool]]] = defaultdict(list)
        self.edges = edges
        for edge in edges:
            subject = str(edge["subject_id"])
            object_id = str(edge["object_id"])
            if subject not in self.nodes or object_id not in self.nodes:
                raise ValueError(f"Graph edge {edge.get('id')} references a missing node")
            self.adjacency[subject].append((object_id, edge, True))
            self.adjacency[object_id].append((subject, edge, False))
        for rows in self.adjacency.values():
            rows.sort(key=lambda row: (str(row[1].get("predicate", "")), row[0], str(row[1].get("id", ""))))
        entity_documents = [
            {
                "id": identifier,
                "title": str(node.get("name", "")),
                "text": " ".join(str(alias) for alias in node.get("aliases", [])),
            }
            for identifier, node in sorted(self.nodes.items())
        ]
        self.entity_documents = entity_documents
        self.entity_bm25 = BM25(entity_documents, k1=entity_k1, b=entity_b)
        self.entity_ids = [str(document["id"]) for document in self.entity_bm25.documents]

    def seed_entities(self, query: str, limit: int = 10) -> list[tuple[str, float]]:
        if limit < 1:
            raise ValueError("Entity seed limit must be positive")
        return [(str(result.document["id"]), float(result.score)) for result in self.entity_bm25.search(query, limit)]

    def expand(
        self,
        query: str,
        *,
        hops: int = 2,
        max_nodes: int = 100,
        max_chunks: int = 30,
        seed_limit: int = 10,
        seed_entity_ids: list[str] | None = None,
    ) -> list[tuple[int, float]]:
        """Return graph-ranked passage indexes, seeded lexically or by an external retriever."""
        if hops < 0 or max_nodes < 1 or max_chunks < 1:
            raise ValueError("hops must be non-negative and node/chunk limits positive")
        if seed_entity_ids is None:
            seeds = self.seed_entities(query, seed_limit)
        else:
            unique_seeds = list(dict.fromkeys(str(identifier) for identifier in seed_entity_ids if str(identifier) in self.nodes))
            seeds = [(identifier, 1.0 / (rank + 1)) for rank, identifier in enumerate(unique_seeds[:seed_limit])]
        if not seeds:
            return []

        node_scores = {identifier: score for identifier, score in seeds[:max_nodes]}
        node_depths = {identifier: 0 for identifier, _ in seeds[:max_nodes]}
        queue = deque(identifier for identifier, _ in seeds[:max_nodes])
        chunk_scores: dict[str, float] = defaultdict(float)
        while queue:
            current = queue.popleft()
            depth = node_depths[current]
            current_score = node_scores[current]
            node = self.nodes[current]
            for chunk_id in node.get("source_chunk_ids", []):
                chunk_id = str(chunk_id)
                if chunk_id in self.passage_index:
                    chunk_scores[chunk_id] = max(chunk_scores[chunk_id], current_score / (depth + 1))
            for neighbor, edge, _forward in self.adjacency.get(current, []):
                evidence = edge.get("evidence", [])
                if not evidence:
                    evidence = [{"source_chunk_id": edge.get("source_chunk_id"), "confidence": edge.get("confidence", 1.0)}]
                confidence = float(edge.get("confidence", max((float(item.get("confidence", 1.0)) for item in evidence), default=1.0)))
                for item in evidence:
                    chunk_id = str(item.get("source_chunk_id", ""))
                    if chunk_id in self.passage_index:
                        evidence_confidence = float(item.get("confidence", confidence))
                        chunk_scores[chunk_id] = max(
                            chunk_scores[chunk_id], current_score * evidence_confidence / (depth + 1)
                        )
                next_depth = depth + 1
                if next_depth > hops or neighbor in node_depths:
                    continue
                next_score = current_score * confidence * 0.5
                if len(node_depths) >= max_nodes or next_score <= 0:
                    continue
                node_depths[neighbor] = next_depth
                node_scores[neighbor] = next_score
                queue.append(neighbor)

        ranked_chunks = sorted(chunk_scores.items(), key=lambda item: (-item[1], item[0]))[:max_chunks]
        return [(self.passage_index[chunk_id], score) for chunk_id, score in ranked_chunks]


class FixedHybridRetriever:
    """Fuse passage BM25 with bounded graph expansion using reciprocal-rank fusion."""

    def __init__(self, passages: list[dict[str, Any]], graph: GraphIndex, *, k1: float = 1.5, b: float = 0.75):
        self.passages = passages
        self.graph = graph
        self.bm25 = BM25(passages, k1=k1, b=b)
        self.passage_index = {str(passage["id"]): index for index, passage in enumerate(passages)}
        if self.passage_index != self.graph.passage_index:
            raise ValueError("Graph index and hybrid retriever must use the same passage IDs and ordering")

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        candidate_k: int = 50,
        hops: int = 2,
        max_nodes: int = 100,
        max_chunks: int = 30,
        seed_limit: int = 10,
        rrf_k: int = 60,
        seed_entity_ids: list[str] | None = None,
        dense_ranking: list[tuple[int, float]] | None = None,
    ) -> list[tuple[dict[str, Any], float]]:
        if top_k < 1 or candidate_k < 1:
            raise ValueError("top_k and candidate_k must be positive")
        lexical = self.bm25.search(query, candidate_k)
        lexical_ranking = [
            (self.passage_index[str(result.document["id"])], result.score) for result in lexical
        ]
        graph_ranking = self.graph.expand(
            query,
            hops=hops,
            max_nodes=max_nodes,
            max_chunks=max_chunks,
            seed_limit=seed_limit,
            seed_entity_ids=seed_entity_ids,
        )
        rankings = [lexical_ranking, graph_ranking]
        if dense_ranking is not None:
            if any(index < 0 or index >= len(self.passages) for index, _score in dense_ranking):
                raise ValueError("Dense ranking contains a passage index outside the configured corpus")
            rankings.append(dense_ranking)
        fused = reciprocal_rank_fusion(*rankings, rrf_k=rrf_k)
        return [(self.passages[index], score) for index, score in fused[:top_k]]
