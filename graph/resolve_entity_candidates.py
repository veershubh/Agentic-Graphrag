"""Generate embedding-ranked entity duplicate candidates for human review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def entity_text(entity: dict[str, Any]) -> str:
    aliases = sorted({str(alias).strip() for alias in entity.get("aliases", []) if str(alias).strip()})
    return "\n".join([str(entity["name"]), *aliases])


def cache_hashes(entities: list[dict[str, Any]]) -> list[str]:
    return [hashlib.sha256(entity_text(entity).encode("utf-8")).hexdigest() for entity in entities]


def load_or_encode(
    entities: list[dict[str, Any]], model_name: str, revision: str, cache_path: Path, batch_size: int, cpu_threads: int
) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer
        import torch
    except ImportError as error:
        raise SystemExit('Install the optional embedding dependency with: python -m pip install -e ".[retrieval]"') from error
    if cpu_threads < 1:
        raise SystemExit("CPU thread count must be positive")
    torch.set_num_threads(cpu_threads)
    ids = [str(entity["id"]) for entity in entities]
    hashes = cache_hashes(entities)
    if cache_path.exists():
        try:
            with np.load(cache_path, allow_pickle=False) as cached:
                metadata = json.loads(str(cached["metadata"].item()))
                if (
                    metadata == {"model": model_name, "revision": revision}
                    and cached["ids"].tolist() == ids
                    and cached["content_hashes"].tolist() == hashes
                ):
                    return np.asarray(cached["embeddings"], dtype=np.float32)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass

    model = SentenceTransformer(model_name, revision=revision, device="cpu")
    embeddings = model.encode(
        [entity_text(entity) for entity in entities],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    with temporary_path.open("wb") as stream:
        np.savez_compressed(
            stream,
            embeddings=embeddings,
            ids=np.asarray(ids),
            content_hashes=np.asarray(hashes),
            metadata=np.asarray(json.dumps({"model": model_name, "revision": revision})),
        )
    temporary_path.replace(cache_path)
    return embeddings


def rank_candidates(
    entities: list[dict[str, Any]], embeddings: np.ndarray, *, threshold: float, neighbors: int, block_size: int = 512
) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    ids = [str(entity["id"]) for entity in entities]
    kinds = [str(entity["kind"]) for entity in entities]
    for start in range(0, len(entities), block_size):
        stop = min(start + block_size, len(entities))
        similarities = embeddings[start:stop] @ embeddings.T
        for local_index, source_index in enumerate(range(start, stop)):
            same_kind = [index for index, kind in enumerate(kinds) if kind == kinds[source_index] and index != source_index]
            best = sorted(same_kind, key=lambda index: (-float(similarities[local_index, index]), ids[index]))[:neighbors]
            for candidate_index in best:
                score = float(similarities[local_index, candidate_index])
                if score < threshold:
                    continue
                left_index, right_index = sorted((source_index, candidate_index), key=lambda index: ids[index])
                key = (ids[left_index], ids[right_index])
                if key in rows:
                    continue
                left, right = entities[left_index], entities[right_index]
                left_aliases = {str(alias).casefold() for alias in left.get("aliases", [])}
                right_aliases = {str(alias).casefold() for alias in right.get("aliases", [])}
                rows[key] = {
                    "entity_id_a": ids[left_index],
                    "kind": kinds[source_index],
                    "name_a": str(left["name"]),
                    "entity_id_b": ids[right_index],
                    "name_b": str(right["name"]),
                    "cosine_similarity": score,
                    "shared_aliases": sorted(left_aliases & right_aliases),
                    "decision": "UNREVIEWED",
                    "canonical_entity_id": "",
                }
    return sorted(rows.values(), key=lambda row: (-row["cosine_similarity"], row["entity_id_a"], row["entity_id_b"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=Path, default=Path("data/processed/domain_graph_nodes.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/entity_resolution_candidates.jsonl"))
    parser.add_argument("--cache", type=Path, default=Path("data/processed/entity_name_embeddings.npz"))
    parser.add_argument("--config", type=Path, default=Path("configs/default.toml"))
    parser.add_argument("--threshold", type=float, default=0.82)
    parser.add_argument("--neighbors", type=int, default=10)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--cpu-threads", type=int)
    args = parser.parse_args()
    if not 0.0 <= args.threshold <= 1.0 or args.neighbors < 1:
        raise SystemExit("Threshold must be in [0, 1] and neighbor count must be positive")

    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    dense_config = config["retrieval"]["dense"]
    model_name = str(dense_config["model"])
    revision = str(dense_config["revision"])
    batch_size = args.batch_size if args.batch_size is not None else int(dense_config.get("batch_size", 64))
    cpu_threads = args.cpu_threads if args.cpu_threads is not None else int(dense_config.get("cpu_threads", 4))
    entities = sorted(read_jsonl(args.nodes), key=lambda entity: str(entity["id"]))
    if batch_size < 1:
        raise SystemExit("Batch size must be positive")
    if len(entities) < 2:
        candidates = []
    else:
        vectors = load_or_encode(entities, model_name, revision, args.cache, batch_size, cpu_threads)
        candidates = rank_candidates(entities, vectors, threshold=args.threshold, neighbors=args.neighbors)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidates), encoding="utf-8")
    summary = {
        "entity_count": len(entities),
        "candidate_pair_count": len(candidates),
        "threshold": args.threshold,
        "neighbors_per_entity": args.neighbors,
        "embedding_model": model_name,
        "embedding_revision": revision,
        "output": str(args.output),
        "note": "Candidates are similarity-ranked suggestions only; no entities are merged automatically.",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
