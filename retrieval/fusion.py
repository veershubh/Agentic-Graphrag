"""Rank fusion helpers."""

from __future__ import annotations


def reciprocal_rank_fusion(*rankings: list[tuple[int, float]], rrf_k: int = 60) -> list[tuple[int, float]]:
    if rrf_k < 1:
        raise ValueError("rrf_k must be at least 1")
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (document_index, _score) in enumerate(ranking, start=1):
            fused[document_index] = fused.get(document_index, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(fused.items(), key=lambda item: (-item[1], item[0]))
