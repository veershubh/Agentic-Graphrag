"""Create deterministic, page-aware passages from locally extracted papers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def passage_id(paper_id: str, page_number: int, chunk_index: int, text: str) -> str:
    digest = hashlib.sha256(f"{paper_id}:{page_number}:{chunk_index}:{text}".encode("utf-8")).hexdigest()[:24]
    return f"passage_{digest}"


def make_passages(paper: dict[str, Any], target_words: int, overlap_words: int) -> list[dict[str, Any]]:
    paper_id = f"arxiv:{paper['arxiv_id']}"
    pages = paper.get("pages") or [paper.get("text", "")]
    target_words = max(1, target_words)
    overlap_words = min(max(0, overlap_words), target_words - 1)
    step = target_words - overlap_words
    passages = []
    for page_number, page_text in enumerate(pages, start=1):
        words = re.findall(r"\S+", page_text)
        for start in range(0, len(words), step):
            text = " ".join(words[start : start + target_words]).strip()
            if not text:
                break
            chunk_index = len(passages)
            passages.append(
                {
                    "id": passage_id(paper_id, page_number, chunk_index, text),
                    "paper_id": paper_id,
                    "arxiv_id": paper["arxiv_id"],
                    "title": paper["title"],
                    "year": paper["year"],
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "text": text,
                }
            )
            if start + target_words >= len(words):
                break
    return passages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/domain_papers.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/domain_passages.jsonl"))
    parser.add_argument("--target-words", type=int, default=500)
    parser.add_argument("--overlap-words", type=int, default=75)
    args = parser.parse_args()

    papers = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    passages = [passage for paper in papers for passage in make_passages(paper, args.target_words, args.overlap_words)]
    if not passages:
        raise SystemExit(f"No passages were produced from {args.input}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in passages), encoding="utf-8")
    print(f"Created {len(passages)} passages from {len(papers)} papers: {args.output}")


if __name__ == "__main__":
    main()

