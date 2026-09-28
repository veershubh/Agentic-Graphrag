"""Local sentence-transformer embeddings and cosine search."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


def document_text(document: dict[str, Any]) -> str:
    return f"{document.get('title', '')}\n{document.get('text', '')}".strip()


def content_hashes(documents: list[dict[str, Any]]) -> list[str]:
    return [hashlib.sha256(document_text(document).encode("utf-8")).hexdigest() for document in documents]


class DenseRetriever:
    def __init__(
        self,
        documents: list[dict[str, Any]],
        model_name: str,
        revision: str,
        cache_path: Path,
        batch_size: int = 64,
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError('Install the optional dependencies with: python -m pip install -e ".[retrieval]"') from error

        self.documents = documents
        self.model_name = model_name
        self.revision = revision
        self.cache_path = cache_path
        self.model = SentenceTransformer(model_name, revision=revision, device="cpu")
        self.embeddings, self.cache_hit = self._load_or_encode(batch_size)

    def _load_or_encode(self, batch_size: int) -> tuple[np.ndarray, bool]:
        ids = [str(document["id"]) for document in self.documents]
        hashes = content_hashes(self.documents)
        if self.cache_path.exists():
            try:
                with np.load(self.cache_path, allow_pickle=False) as cached:
                    metadata = json.loads(str(cached["metadata"].item()))
                    if (
                        metadata == {"model": self.model_name, "revision": self.revision}
                        and cached["ids"].tolist() == ids
                        and cached["content_hashes"].tolist() == hashes
                    ):
                        return np.asarray(cached["embeddings"], dtype=np.float32), True
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                pass

        vectors = self.model.encode_document(
            [document_text(document) for document in self.documents],
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        with temporary_path.open("wb") as stream:
            np.savez_compressed(
                stream,
                embeddings=vectors,
                ids=np.asarray(ids),
                content_hashes=np.asarray(hashes),
                metadata=np.asarray(json.dumps({"model": self.model_name, "revision": self.revision})),
            )
        temporary_path.replace(self.cache_path)
        return vectors, False

    def search_many(self, queries: list[str], top_k: int, batch_size: int = 64) -> list[list[tuple[int, float]]]:
        query_vectors = self.model.encode_query(
            queries,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)
        similarities = query_vectors @ self.embeddings.T
        limit = min(top_k, len(self.documents))
        rankings = []
        ids = [str(document["id"]) for document in self.documents]
        for row in similarities:
            indices = sorted(range(len(row)), key=lambda index: (-float(row[index]), ids[index]))[:limit]
            rankings.append([(index, float(row[index])) for index in indices])
        return rankings
