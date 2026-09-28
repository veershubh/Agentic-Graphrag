"""Collect a versioned candidate bibliography from arXiv's public search page."""

from __future__ import annotations

import argparse
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://arxiv.org/search/"
USER_AGENT = "AgenticGraphRAG/0.1 (https://github.com/veershubh/Agentic-Graphrag)"
RESULT_SIZE = 200
REQUEST_DELAY_SECONDS = 3.1
TOPICS = ("evaluation", "benchmark")


class Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


class ClassText(HTMLParser):
    def __init__(self, class_name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.wanted = set(class_name.split())
        self.stack: list[str] = []
        self.target_depth: int | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set(dict(attrs).get("class", "").split())
        if self.target_depth is None and self.wanted <= classes:
            self.target_depth = len(self.stack)
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.stack and self.stack[-1] == tag:
            if self.target_depth == len(self.stack) - 1:
                self.target_depth = None
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.target_depth is not None:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def field(block: str, class_name: str) -> str:
    parser = ClassText(class_name)
    parser.feed(block)
    return parser.text()


def parse_results(page: str, query: str) -> list[dict[str, str]]:
    results = []
    for block in re.findall(r'<li\b[^>]*class="[^"]*\barxiv-result\b[^"]*"[^>]*>(.*?)</li>', page, re.DOTALL):
        id_match = re.search(r'href="https://arxiv\.org/abs/([^"?#]+)', block)
        if not id_match:
            continue
        identifier = id_match.group(1).split("v", 1)[0]
        abstract = field(block, "abstract-full") or field(block, "abstract-short")
        if abstract.lower().startswith("abstract:"):
            abstract = abstract[len("abstract:") :].strip()
        date_match = re.search(r"\[Submitted on ([^\]]+)\]", block)
        authors = field(block, "authors")
        if authors.startswith("Authors:"):
            authors = authors[len("Authors:") :].strip()
        results.append(
            {
                "arxiv_id": identifier,
                "title": field(block, "title"),
                "authors": authors,
                "abstract": abstract,
                "categories": ", ".join(re.findall(r">([a-z-]+\.[A-Z]{2})</span>", block)),
                "submitted": date_match.group(1) if date_match else "",
                "abstract_url": f"https://arxiv.org/abs/{identifier}",
                "pdf_url": f"https://arxiv.org/pdf/{identifier}",
                "search_query": query,
            }
        )
    return results


def fetch_page(topic: str, year: int, start: int = 0) -> list[dict[str, str]]:
    params = {
        "advanced": "1",
        "terms-0-operator": "AND",
        "terms-0-term": "large language model",
        "terms-0-field": "abstract",
        "terms-1-operator": "AND",
        "terms-1-term": topic,
        "terms-1-field": "abstract",
        "date-filter_by": "specific_year",
        "date-year": str(year),
        "date-date_type": "announced_date_first",
        "abstracts": "show",
        "order": "-announced_date_first",
        "size": str(RESULT_SIZE),
        "start": str(start),
        "classification-computer_science": "y",
        "classification-include_cross_list": "include",
    }
    request = Request(BASE_URL + "advanced?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        page = response.read().decode("utf-8", errors="replace")
    return parse_results(page, f"abstract:large language model AND {topic}; announced year {year}")


def collect(limit: int, first_year: int, last_year: int) -> list[dict[str, str]]:
    years = list(range(first_year, last_year + 1))
    if not years:
        return []
    base, remainder = divmod(limit, len(years))
    year_quotas = {year: base + (index < remainder) for index, year in enumerate(years)}
    records: dict[str, dict[str, str]] = {}
    for year in years:
        quota = year_quotas[year]
        topic_quota, topic_remainder = divmod(quota, len(TOPICS))
        collected_for_year = 0
        for topic_index, topic in enumerate(TOPICS):
            topic_limit = topic_quota + (topic_index < topic_remainder)
            offset = 0
            while topic_limit > 0:
                if records:
                    time.sleep(REQUEST_DELAY_SECONDS)
                page_records = fetch_page(topic, year, offset)
                if not page_records:
                    break
                added = 0
                for record in page_records:
                    if record["arxiv_id"] in records:
                        continue
                    records[record["arxiv_id"]] = record
                    added += 1
                    collected_for_year += 1
                    topic_limit -= 1
                    if topic_limit == 0:
                        break
                if added == 0 or len(page_records) < RESULT_SIZE:
                    break
                offset += RESULT_SIZE
        # If overlapping topic results reduced this year's yield, keep its observed count
        # rather than silently filling it with papers from a different year.
        print(f"{year}: {collected_for_year}/{quota} candidates")
    return sorted(records.values(), key=lambda row: (row["submitted"], row["arxiv_id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--first-year", type=int, default=2020)
    parser.add_argument("--last-year", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=Path("data/raw/arxiv_candidates.jsonl"))
    args = parser.parse_args()
    rows = collect(args.limit, args.first_year, args.last_year)
    if not rows:
        raise SystemExit("arXiv search returned no records")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"Saved {len(rows)} candidate records to {args.output}")


if __name__ == "__main__":
    main()

