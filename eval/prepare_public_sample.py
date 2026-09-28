"""Create a deterministic, hop-stratified MuSiQue public evaluation slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SOURCE = "MuSiQue-Ans v1.0 validation"
SOURCE_URL = "https://github.com/stonybrooknlp/musique"
SAMPLE_SEED = 20260928


def paragraph_id(paragraph: dict[str, Any]) -> str:
    key = hashlib.sha256(
        f"{paragraph.get('title', '')}\n{paragraph.get('paragraph_text', '')}".encode("utf-8")
    ).hexdigest()[:20]
    return f"musique_para_{key}"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    paragraphs = record.get("paragraphs", [])
    decomposition = record.get("question_decomposition", [])
    supports = []
    for step in decomposition:
        indices = step.get("paragraph_support_idx", [])
        if isinstance(indices, int):
            indices = [indices]
        for idx in indices:
            if idx not in supports:
                supports.append(idx)
    if not supports:
        supports = [p["idx"] for p in paragraphs if p.get("is_supporting")]
    hop_count = len(decomposition) if decomposition else len(supports)
    if hop_count < 1:
        raise ValueError(f"Question {record.get('id')} has no hop/support labels")
    paragraphs_by_index = {p["idx"]: p for p in paragraphs}
    missing = set(supports) - paragraphs_by_index.keys()
    if missing:
        raise ValueError(f"Question {record.get('id')} references missing paragraphs: {sorted(missing)}")
    return {
        "id": str(record["id"]),
        "question": record["question"],
        "answer": record.get("answer", ""),
        "answer_aliases": record.get("answer_aliases", []),
        "hop_count": hop_count,
        "is_answerable": True,
        "supporting_paragraph_ids": [paragraph_id(paragraphs_by_index[idx]) for idx in supports],
        "source": SOURCE,
        "source_url": SOURCE_URL,
    }


def sample_records(records: list[dict[str, Any]], size: int = 300) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        normalized = normalize_record(record)
        groups[normalized["hop_count"]].append(normalized)
    hops = sorted(groups)
    if sum(map(len, groups.values())) < size:
        raise ValueError(f"Requested {size} examples from only {sum(map(len, groups.values()))} records")
    rng = random.Random(SAMPLE_SEED)
    for group in groups.values():
        group.sort(key=lambda row: row["id"])
        rng.shuffle(group)
    allocation = {hop: size // len(hops) for hop in hops}
    for hop in hops[: size % len(hops)]:
        allocation[hop] += 1
    selected: list[dict[str, Any]] = []
    remaining = size
    for hop in hops:
        take = min(allocation[hop], len(groups[hop]))
        selected.extend(groups[hop][:take])
        remaining -= take
    if remaining:
        for hop in hops:
            spare = groups[hop][allocation[hop] :]
            take = min(len(spare), remaining)
            selected.extend(spare[:take])
            remaining -= take
            if not remaining:
                break
    selected.sort(key=lambda row: (row["hop_count"], row["id"]))
    return selected


def build_corpus(source_records: list[dict[str, Any]], selected_ids: set[str]) -> list[dict[str, Any]]:
    by_id = {str(record["id"]): record for record in source_records}
    passages: dict[str, dict[str, Any]] = {}
    for question_id in sorted(selected_ids):
        record = by_id[question_id]
        supports = set(normalize_record(record)["supporting_paragraph_ids"])
        for paragraph in record.get("paragraphs", []):
            passage_id = paragraph_id(paragraph)
            entry = passages.setdefault(
                passage_id,
                {
                    "id": passage_id,
                    "title": paragraph.get("title", ""),
                    "text": paragraph.get("paragraph_text", ""),
                    "source": SOURCE,
                    "supporting_for": [],
                },
            )
            if passage_id in supports and question_id not in entry["supporting_for"]:
                entry["supporting_for"].append(question_id)
    return sorted(passages.values(), key=lambda passage: passage["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Official musique_ans_v1.0_dev.jsonl")
    parser.add_argument("--questions", type=Path, default=Path("eval/data/public/musique_v1.0_300.jsonl"))
    parser.add_argument("--corpus", type=Path, default=Path("eval/data/public/musique_v1.0_corpus.jsonl"))
    parser.add_argument("--size", type=int, default=300)
    args = parser.parse_args()

    source_records = load_jsonl(args.source)
    questions = sample_records(source_records, args.size)
    corpus = build_corpus(source_records, {q["id"] for q in questions})
    question_ids = {question["id"] for question in questions}
    corpus_by_id = {passage["id"]: passage for passage in corpus}
    if len(question_ids) != args.size:
        raise ValueError(f"Expected {args.size} distinct questions; got {len(question_ids)}")
    for question in questions:
        missing = set(question["supporting_paragraph_ids"]) - corpus_by_id.keys()
        if not question["answer"] or missing:
            raise ValueError(f"Question {question['id']} has an empty answer or missing evidence: {sorted(missing)}")
    for passage in corpus:
        if not set(passage["supporting_for"]) <= question_ids:
            raise ValueError(f"Passage {passage['id']} links to a question outside this sample")
    for path, rows in ((args.questions, questions), (args.corpus, corpus)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"Questions: {len(questions)}; hops: {dict(sorted(Counter(q['hop_count'] for q in questions).items()))}")
    print(f"Unique candidate paragraphs: {len(corpus)}; supporting links: {sum(len(p['supporting_for']) for p in corpus)}")
    print(f"Question file: {args.questions}\nCorpus file: {args.corpus}")


if __name__ == "__main__":
    main()

