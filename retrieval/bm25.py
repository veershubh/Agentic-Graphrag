"""Small dependency-free BM25 retriever for the public benchmark baseline."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


@dataclass(frozen=True)
class SearchResult:
    document: dict[str, Any]
    score: float


class BM25:
    """Okapi BM25 over a fixed set of short documents."""

    def __init__(self, documents: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        if not documents:
            raise ValueError("BM25 requires at least one document")
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 parameters require k1 > 0 and 0 <= b <= 1")
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(f"{doc.get('title', '')} {doc.get('text', '')}") for doc in documents]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.average_length = sum(self.lengths) / len(self.lengths) or 1.0
        self.term_frequencies = [Counter(tokens) for tokens in self.tokens]
        document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            document_frequency.update(frequencies.keys())
        count = len(documents)
        self.inverse_document_frequency = {
            term: math.log(1.0 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_terms = set(tokenize(query))
        scores = []
        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            length_norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average_length)
            for term in query_terms:
                term_frequency = frequencies.get(term, 0)
                if term_frequency:
                    numerator = term_frequency * (self.k1 + 1)
                    denominator = term_frequency + length_norm
                    score += self.inverse_document_frequency[term] * numerator / denominator
            if score > 0:
                scores.append(SearchResult(self.documents[index], score))
        scores.sort(key=lambda result: (-result.score, str(result.document.get("id", ""))))
        return scores[:top_k]
