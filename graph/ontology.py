"""Constrained graph ontology and evidence-backed extraction normalization."""

from __future__ import annotations

import hashlib
import re
from typing import Any


ENTITY_KINDS = ("Paper", "Method", "Dataset", "Metric", "Task")
PREDICATES = ("PROPOSES", "EVALUATES_ON", "USES", "OUTPERFORMS", "CITES")
ALLOWED_ENDPOINTS = {
    "PROPOSES": ({"Paper"}, {"Method"}),
    "EVALUATES_ON": ({"Paper", "Method"}, {"Dataset", "Task", "Metric"}),
    "USES": ({"Paper", "Method"}, {"Method", "Dataset", "Metric", "Task"}),
    "OUTPERFORMS": ({"Method"}, {"Method"}),
    "CITES": ({"Paper"}, {"Paper"}),
}


def normalize_name(name: str) -> str:
    return " ".join(re.findall(r"\w+", name.casefold(), flags=re.UNICODE))


def stable_entity_id(kind: str, name: str) -> str:
    normalized = normalize_name(name)
    if kind not in ENTITY_KINDS or not normalized:
        raise ValueError(f"Invalid graph entity: kind={kind!r}, name={name!r}")
    digest = hashlib.sha256(f"{kind}:{normalized}".encode("utf-8")).hexdigest()[:20]
    return f"{kind.casefold()}_{digest}"


def extraction_records(
    result: dict[str, Any],
    *,
    chunk_id: str,
    paper_id: str,
    paper_title: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    endpoint_keys: dict[tuple[str, str], tuple[str, str]] = {}
    ambiguous_aliases: set[tuple[str, str]] = set()
    source_paper = {"kind": "Paper", "name": paper_title, "aliases": [paper_id]}
    for entity in [source_paper, *result.get("entities", [])]:
        kind = entity.get("kind")
        name = " ".join(str(entity.get("name", "")).split())
        normalized = normalize_name(name)
        if kind not in ENTITY_KINDS or not normalized:
            raise ValueError(f"Invalid entity returned for source chunk {chunk_id}: {entity!r}")
        key = (kind, normalized)
        current = entities_by_key.get(key)
        aliases = sorted({str(alias).strip() for alias in entity.get("aliases", []) if str(alias).strip()})
        if current is None:
            entities_by_key[key] = {
                "id": stable_entity_id(kind, name),
                "kind": kind,
                "name": name,
                "aliases": aliases,
                "source_chunk_ids": [chunk_id],
                "paper_ids": [paper_id],
            }
        else:
            current["aliases"] = sorted(set(current["aliases"]) | set(aliases))
        canonical_key = key
        for alias in [name, *aliases]:
            alias_key = (kind, normalize_name(alias))
            previous = endpoint_keys.get(alias_key)
            if previous is None and alias_key not in ambiguous_aliases:
                endpoint_keys[alias_key] = canonical_key
            elif previous != canonical_key:
                endpoint_keys.pop(alias_key, None)
                ambiguous_aliases.add(alias_key)

    triples = []
    for triple in result.get("triples", []):
        subject_kind = triple.get("subject_kind")
        object_kind = triple.get("object_kind")
        predicate = triple.get("predicate")
        subject_key = endpoint_keys.get((subject_kind, normalize_name(str(triple.get("subject", "")))))
        object_key = endpoint_keys.get((object_kind, normalize_name(str(triple.get("object", "")))))
        if predicate not in PREDICATES:
            raise ValueError(f"Unsupported relation {predicate!r} in source chunk {chunk_id}")
        allowed_subject, allowed_object = ALLOWED_ENDPOINTS[predicate]
        if subject_kind not in allowed_subject or object_kind not in allowed_object:
            raise ValueError(f"Invalid endpoint kinds for {predicate}: {subject_kind} -> {object_kind}")
        if subject_key not in entities_by_key or object_key not in entities_by_key:
            raise ValueError(f"Relation endpoint missing from extracted entities in source chunk {chunk_id}")
        confidence = float(triple.get("confidence", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Relation confidence out of range in source chunk {chunk_id}")
        subject_id = entities_by_key[subject_key]["id"]
        object_id = entities_by_key[object_key]["id"]
        triple_fingerprint = f"{chunk_id}:{subject_id}:{predicate}:{object_id}"
        triples.append(
            {
                "id": "edge_" + hashlib.sha256(triple_fingerprint.encode("utf-8")).hexdigest()[:20],
                "subject_id": subject_id,
                "predicate": predicate,
                "object_id": object_id,
                "confidence": confidence,
                "source_chunk_id": chunk_id,
                "paper_id": paper_id,
            }
        )
    entities = sorted(entities_by_key.values(), key=lambda item: item["id"])
    triples.sort(key=lambda item: item["id"])
    return entities, triples
