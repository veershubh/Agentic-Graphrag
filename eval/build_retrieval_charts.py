"""Build hop-split SVG charts from saved retrieval artifacts without changing them."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_SOURCE = "domain_graph_dense_entity_seed_v0.1.json"
PUBLIC_SOURCE = "public_hybrid_v0.1.json"
COLORS = ("#2463a6", "#c25136", "#3d8b62", "#8055a3", "#cc8b17", "#327e89", "#bd4b80", "#65717d")


def read_retrievers(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["retrievers"]


def panel_svg(name: str, metrics: dict[str, Any], x0: int, y0: int, color: str) -> str:
    width, height = 286, 205
    left, right, top, bottom = 38, 12, 34, 39
    plot_x, plot_y = x0 + left, y0 + top
    plot_w, plot_h = width - left - right, height - top - bottom
    hops = sorted(metrics["by_hop"], key=int)
    xs = {hop: plot_x + plot_w * index / max(1, len(hops) - 1) for index, hop in enumerate(hops)}
    y = lambda value: plot_y + plot_h * (1 - value)
    parts = [f'<g aria-label="{html.escape(name)}">']
    parts.append(f'<text x="{x0 + width / 2}" y="{y0 + 18}" text-anchor="middle" class="title">{html.escape(name)}</text>')
    for tick in (0.0, 0.5, 1.0):
        yy = y(tick)
        parts.append(f'<line x1="{plot_x}" y1="{yy:.1f}" x2="{plot_x + plot_w}" y2="{yy:.1f}" class="grid"/>')
        parts.append(f'<text x="{plot_x - 7}" y="{yy + 4:.1f}" text-anchor="end" class="axis">{tick:.1f}</text>')
    points = []
    for hop in hops:
        row = metrics["by_hop"][hop]
        xx = xs[hop]
        value = float(row["supporting_recall_at_k"])
        low, high = map(float, row["bootstrap_95_ci"])
        points.append(f"{xx:.1f},{y(value):.1f}")
        parts.append(f'<line x1="{xx:.1f}" y1="{y(high):.1f}" x2="{xx:.1f}" y2="{y(low):.1f}" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<line x1="{xx - 4:.1f}" y1="{y(high):.1f}" x2="{xx + 4:.1f}" y2="{y(high):.1f}" stroke="{color}"/>')
        parts.append(f'<line x1="{xx - 4:.1f}" y1="{y(low):.1f}" x2="{xx + 4:.1f}" y2="{y(low):.1f}" stroke="{color}"/>')
        parts.append(f'<circle cx="{xx:.1f}" cy="{y(value):.1f}" r="3.5" fill="{color}"/>')
        parts.append(f'<text x="{xx:.1f}" y="{plot_y + plot_h + 16}" text-anchor="middle" class="axis">{hop}-hop</text>')
    parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
    parts.append(f'<text x="{x0 + width / 2}" y="{y0 + height - 4}" text-anchor="middle" class="axis">Recall@5 (95% bootstrap interval)</text>')
    parts.append("</g>")
    return "\n".join(parts)


def build_chart(title: str, retrievers: dict[str, dict[str, Any]], output: Path) -> None:
    width = 286 * 2
    rows = (len(retrievers) + 1) // 2
    height = 205 * rows + 56
    panels = [
        panel_svg(name, metrics, (index % 2) * 286, 42 + (index // 2) * 205, COLORS[index % len(COLORS)])
        for index, (name, metrics) in enumerate(retrievers.items())
    ]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
<style>text{{font-family:Arial,sans-serif;fill:#18212b}}.headline{{font-size:18px;font-weight:700}}.title{{font-size:13px;font-weight:700}}.axis{{font-size:10px;fill:#465363}}.grid{{stroke:#dce2e9;stroke-width:1}}</style>
<text x="{width / 2}" y="24" text-anchor="middle" class="headline">{html.escape(title)}</text>
{''.join(panels)}
</svg>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    domain = read_retrievers(ROOT / "eval" / "results" / DOMAIN_SOURCE)
    public = read_retrievers(ROOT / "eval" / "results" / PUBLIC_SOURCE)
    build_chart("Domain retrieval by hop (provisional corpus)", domain, args.output_dir / "retrieval-domain-by-hop-v0.1.svg")
    build_chart("MuSiQue retrieval by hop", public, args.output_dir / "retrieval-public-by-hop-v0.1.svg")
    print(f"Wrote hop-split charts to {args.output_dir}")


if __name__ == "__main__":
    main()
