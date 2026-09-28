"""Download a year-balanced subset of the frozen arXiv paper references."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "AgenticGraphRAG/0.1 (https://github.com/veershubh/Agentic-Graphrag)"


def read_references(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def choose_references(rows: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    groups: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[int(row["year"])].append(row)
    if limit <= 0 or limit >= len(rows):
        return sorted(rows, key=lambda row: (int(row["year"]), -int(row["selection_score"]), str(row["arxiv_id"])))
    years = sorted(groups)
    per_year, remainder = divmod(limit, len(years))
    selected = []
    for index, year in enumerate(years):
        quota = per_year + (index < remainder)
        ranked = sorted(
            groups[year],
            key=lambda row: (-int(row["selection_score"]), str(row["arxiv_id"])),
        )
        selected.extend(ranked[:quota])
    if len(selected) != limit:
        raise ValueError(f"Cannot select {limit} papers from {len(rows)} references")
    return selected


def download_one(reference: dict[str, object], paper_dir: Path) -> dict[str, object]:
    identifier = str(reference["arxiv_id"])
    target = paper_dir / f"{identifier}.pdf"
    if target.exists() and target.stat().st_size > 0:
        return {
            "arxiv_id": identifier,
            "status": "already_present",
            "path": str(target),
            "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    request = Request(str(reference["pdf_url"]), headers={"User-Agent": USER_AGENT})
    partial = target.with_suffix(".pdf.part")
    try:
        with urlopen(request, timeout=90) as response, partial.open("wb") as stream:
            shutil.copyfileobj(response, stream)
    except (HTTPError, URLError, TimeoutError) as exc:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download arXiv:{identifier}: {exc}") from exc
    with partial.open("rb") as stream:
        signature = stream.read(5)
    if signature != b"%PDF-":
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"arXiv:{identifier} did not return a PDF")
    digest = hashlib.sha256(partial.read_bytes()).hexdigest()
    size = partial.stat().st_size
    partial.replace(target)
    return {
        "arxiv_id": identifier,
        "status": "downloaded",
        "path": str(target),
        "bytes": size,
        "sha256": digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, default=Path("eval/data/domain/papers_candidates.jsonl"))
    parser.add_argument("--paper-dir", type=Path, default=Path("data/raw/papers"))
    parser.add_argument("--limit", type=int, default=20, help="Balanced pilot count; 0 downloads all references")
    parser.add_argument("--delay-seconds", type=float, default=3.1)
    parser.add_argument("--manifest", type=Path, default=Path("data/raw/paper_downloads.jsonl"))
    args = parser.parse_args()

    references = choose_references(read_references(args.references), args.limit)
    args.paper_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for index, reference in enumerate(references):
        paper_path = args.paper_dir / f"{reference['arxiv_id']}.pdf"
        if index and not paper_path.exists():
            time.sleep(args.delay_seconds)
        try:
            result = download_one(reference, args.paper_dir)
        except RuntimeError as exc:
            result = {"arxiv_id": reference["arxiv_id"], "status": "failed", "error": str(exc)}
        result["title"] = reference["title"]
        result["year"] = reference["year"]
        results.append(result)
        args.manifest.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8")
        print(f"{index + 1}/{len(references)} {result['arxiv_id']} {result['status']}", flush=True)
    total_bytes = sum(int(row.get("bytes", 0)) for row in results)
    failed = sum(row["status"] == "failed" for row in results)
    successful = len(results) - failed
    print(f"Downloaded/present: {successful}; failed: {failed}; PDF bytes recorded: {total_bytes}")


if __name__ == "__main__":
    main()

