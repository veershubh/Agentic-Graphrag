"""Download the official MuSiQue v1.0 release and extract its validation split."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path


ARCHIVE_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=1tGdADlNjWFaHLeZZGShh2IRcpO6Lv24h&export=download&confirm=t"
)
ARCHIVE_NAME = "musique_data_v1.0.zip"
SPLIT_NAME = "musique_ans_v1.0_dev.jsonl"
EXPECTED_ARCHIVE_SHA256 = "98f839bf2fd5319f5c688aed77901a6d5c30b3b9f9f691ab9a8ecafb045ee0cd"
EXPECTED_SPLIT_SHA256 = "15fa63794d18a94ce12411aca6e2327e65b6e83b0b1490efab3f1962e48abf3b"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_and_extract(raw_dir: Path) -> tuple[Path, str]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive_path = raw_dir / ARCHIVE_NAME
    if not archive_path.exists():
        request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "agentic-graphrag/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as target:
            shutil.copyfileobj(response, target)
    archive_hash = sha256(archive_path)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(f"MuSiQue archive SHA-256 mismatch: {archive_hash}")
    with zipfile.ZipFile(archive_path) as archive:
        candidates = [name for name in archive.namelist() if Path(name).name == SPLIT_NAME]
        if len(candidates) != 1:
            raise ValueError(f"Expected one {SPLIT_NAME} in {ARCHIVE_NAME}; found {len(candidates)}")
        output_path = raw_dir / SPLIT_NAME
        with archive.open(candidates[0]) as source, output_path.open("wb") as target:
            shutil.copyfileobj(source, target)
    split_hash = sha256(output_path)
    if split_hash != EXPECTED_SPLIT_SHA256:
        raise ValueError(f"MuSiQue validation split SHA-256 mismatch: {split_hash}")
    return output_path, archive_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    split_path, archive_hash = download_and_extract(args.raw_dir)
    print(f"Extracted {split_path}")
    print(f"Archive SHA-256: {archive_hash}")


if __name__ == "__main__":
    main()

