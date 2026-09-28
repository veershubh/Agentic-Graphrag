"""Extract clean text from locally downloaded arXiv PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, default=Path("eval/data/domain/papers_candidates.jsonl"))
    parser.add_argument("--paper-dir", type=Path, default=Path("data/raw/papers"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/domain_papers.jsonl"))
    args = parser.parse_args()

    try:
        import pymupdf
    except ImportError as exc:
        raise SystemExit('Install the PDF extraction extra with: python -m pip install -e ".[papers]"') from exc

    references = {
        str(row["arxiv_id"]): row
        for row in (json.loads(line) for line in args.references.read_text(encoding="utf-8").splitlines())
        if row
    }
    extracted = []
    for pdf_path in sorted(args.paper_dir.glob("*.pdf")):
        identifier = pdf_path.stem
        reference = references.get(identifier)
        if reference is None:
            continue
        with pymupdf.open(pdf_path) as pdf:
            pages = [page.get_text("text") for page in pdf]
            text = "\n\n".join(pages)
            text = text.replace("\x00", "")
            text = re.sub(r"[ \t]+\n", "\n", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            extracted.append(
                {
                    "arxiv_id": identifier,
                    "title": reference["title"],
                    "authors": reference["authors"],
                    "year": reference["year"],
                    "abstract_url": reference["abstract_url"],
                    "pdf_sha256": sha256(pdf_path),
                    "rights_status": "not_checked; local research use only",
                    "page_count": len(pdf),
                    "character_count": len(text),
                    "pages": pages,
                    "text": text,
                }
            )
    if not extracted:
        raise SystemExit(f"No PDFs matching references found in {args.paper_dir}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in extracted), encoding="utf-8")
    total_chars = sum(row["character_count"] for row in extracted)
    print(f"Extracted {len(extracted)} papers, {total_chars:,} characters to {args.output}")


if __name__ == "__main__":
    main()

