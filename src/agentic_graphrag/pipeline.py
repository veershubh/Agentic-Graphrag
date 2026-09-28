"""Dependency-free local document normalization and chunking smoke pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def parse_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    metadata: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        _, front_matter, body = text.split("---", 2)
        for line in front_matter.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"\'')
    title = metadata.get("title", path.stem.replace("-", " ").title())
    return {
        "id": stable_id("doc", path.name),
        "title": title,
        "authors": [author.strip() for author in metadata.get("authors", "").split(",") if author.strip()],
        "year": int(metadata["year"]) if metadata.get("year", "").isdigit() else None,
        "source_id": metadata.get("source_id", path.stem),
        "text": body.strip(),
    }


def stable_id(kind: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{kind}_{digest}"


def chunk_document(document: dict[str, Any], target_words: int, overlap_words: int) -> list[dict[str, Any]]:
    words = re.findall(r"\S+", document["text"])
    if not words:
        return []
    target_words = max(1, target_words)
    overlap_words = min(max(0, overlap_words), target_words - 1)
    step = target_words - overlap_words
    chunks = []
    for start in range(0, len(words), step):
        content = " ".join(words[start : start + target_words])
        if not content:
            break
        chunks.append(
            {
                "id": stable_id("chunk", f"{document['id']}:{start}:{content}"),
                "document_id": document["id"],
                "chunk_index": len(chunks),
                "text": content,
            }
        )
        if start + target_words >= len(words):
            break
    return chunks


def run_pipeline(input_dir: Path, output_path: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    chunk_config = config["chunking"]
    # This wiring-only smoke stage uses words as a dependency-free proxy for tokens.
    target_words = int(chunk_config["target_tokens"])
    overlap_words = int(chunk_config["overlap_tokens"])
    documents = [parse_markdown(path) for path in sorted(input_dir.glob("*.md"))]
    if not documents:
        raise ValueError(f"No Markdown documents found in {input_dir}")
    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(document, target_words, overlap_words)
    ]
    artifact = {
        "pipeline_version": 1,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "documents": documents,
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/smoke"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/smoke.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    args = parser.parse_args()
    artifact = run_pipeline(args.input, args.output, args.config)
    print(f"Processed {artifact['document_count']} documents into {artifact['chunk_count']} chunks: {args.output}")


if __name__ == "__main__":
    main()

