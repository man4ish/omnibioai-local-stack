#!/usr/bin/env python3
"""
OmniBioAI Platform — Interactive Architecture + Codebase Statistics Report (Plotly)

What it does
------------
1) Runs `cloc` (JSON) over multiple repos/files with strict excludes
2) Produces an INTERACTIVE HTML report containing:
   - Professional architecture flow diagram (layered boxes + arrows)
   - Project-wise contribution (pie + bar)
   - Language-wise contribution overall (pie + bar)
   - Summary tables (projects + languages)

Usage
-----
# From repo root (e.g. ~/Desktop/machine):
python utils/report_generator.py

# Or specify paths:
python utils/report_generator.py omnibioai omnibioai-tool-exec ragbio lims-x

Requirements
------------
- cloc installed and on PATH
- plotly installed: pip install plotly

Output
------
- out/reports/omnibioai_codebase_report.html
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Union

import plotly.graph_objects as go


# ------------------------------------------------------------------------------
# cloc exclusions (keep aligned with your safe excludes)
# ------------------------------------------------------------------------------
EXCLUDE_DIRS = (
    "obsolete,staticfiles,node_modules,.venv,env,__pycache__,migrations,"
    "admin,venv,gnn_env,venv_sys,work,input,demo"
)
EXCLUDE_EXTS = "svg,json,txt,csv,lock,min.js,map,md"
NOT_MATCH_D = r"(data|uploads|downloads|cache|results|logs)"


# ------------------------------------------------------------------------------
# Data model
# ------------------------------------------------------------------------------
@dataclass
class Totals:
    files: int = 0
    blank: int = 0
    comment: int = 0
    code: int = 0

    def add(self, other: "Totals") -> None:
        self.files += other.files
        self.blank += other.blank
        self.comment += other.comment
        self.code += other.code


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def fmt_int(n: int) -> str:
    return f"{n:,}"


def safe_div(a: float, b: float) -> float:
    return (a / b) if b else 0.0


def ensure_cloc() -> None:
    if shutil.which("cloc") is None:
        print("ERROR: cloc is not installed or not on PATH.", file=sys.stderr)
        print("Install: sudo apt-get install cloc  (or: conda install -c conda-forge cloc)", file=sys.stderr)
        raise SystemExit(2)


def run_cloc(path: Path) -> Tuple[Totals, Dict[str, Totals]]:
    """
    Returns:
      - overall totals
      - per-language totals dict
    """
    cmd = [
        "cloc",
        str(path),
        "--exclude-dir",
        EXCLUDE_DIRS,
        "--exclude-ext",
        EXCLUDE_EXTS,
        "--fullpath",
        "--not-match-d",
        NOT_MATCH_D,
        "--json",
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"cloc failed for {path}:\n{proc.stderr.strip()}")

    data = json.loads(proc.stdout)

    if "SUM" not in data:
        raise RuntimeError(f"Unexpected cloc JSON output for {path} (missing SUM).")

    sum_row = data["SUM"]
    overall = Totals(
        files=int(sum_row.get("nFiles", 0)),
        blank=int(sum_row.get("blank", 0)),
        comment=int(sum_row.get("comment", 0)),
        code=int(sum_row.get("code", 0)),
    )

    per_lang: Dict[str, Totals] = {}
    for k, v in data.items():
        if k in ("header", "SUM"):
            continue
        if isinstance(v, dict) and "code" in v:
            per_lang[k] = Totals(
                files=int(v.get("nFiles", 0)),
                blank=int(v.get("blank", 0)),
                comment=int(v.get("comment", 0)),
                code=int(v.get("code", 0)),
            )

    return overall, per_lang


def validate_paths(paths: List[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print("ERROR: These paths do not exist:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        raise SystemExit(2)


# ------------------------------------------------------------------------------
# Architecture diagram (Professional flow diagram)
# ------------------------------------------------------------------------------
def build_architecture_spec(existing_projects: List[str]) -> Tuple[List[str], List[Tuple[str, str]], Dict[str, str]]:
    """
    Professional layered architecture spec.

    Returns:
      nodes: list of node ids (strings)
      edges: list of (src, dst)
      node_layer: node -> layer name
    """
    layers = {
        "Dev / Clients": [
            "ai-dev-docker",
            "omnibioai_sdk",
        ],
        "Workbench": [
            "omnibioai",
            "lims-x",
            "ragbio",
        ],
        "Services": [
            "omnibioai-toolserver",
        ],
        "Execution": [
            "omnibioai-tool-exec",
        ],
        "Tool Runners": [
            "aws-tools",
        ],
        "Infra / Ops": [
            "k8s",
            "db-init",
            "docker-compose.yml",
            "start_stack_tmux.sh",
            "smoke_test_stack.sh",
        ],
    }

    node_layer: Dict[str, str] = {}
    nodes: List[str] = []
    for layer_name, layer_nodes in layers.items():
        for n in layer_nodes:
            if n in existing_projects:
                nodes.append(n)
                node_layer[n] = layer_name

    # Flow edges (left -> right). Keep this “diagrammatic”, not exhaustively accurate.
    edges_wanted = [
        ("ai-dev-docker", "omnibioai"),
        ("omnibioai_sdk", "omnibioai"),

        ("omnibioai", "lims-x"),
        ("omnibioai", "ragbio"),
        ("omnibioai", "omnibioai-toolserver"),

        ("omnibioai-toolserver", "omnibioai-tool-exec"),
        ("omnibioai-tool-exec", "aws-tools"),

        # Infra edges (lightweight)
        ("docker-compose.yml", "omnibioai"),
        ("docker-compose.yml", "omnibioai-toolserver"),
        ("docker-compose.yml", "omnibioai-tool-exec"),
        ("start_stack_tmux.sh", "docker-compose.yml"),
        ("smoke_test_stack.sh", "docker-compose.yml"),
        ("k8s", "omnibioai"),
        ("k8s", "omnibioai-toolserver"),
        ("k8s", "omnibioai-tool-exec"),
        ("db-init", "omnibioai"),
    ]

    edges = [(a, b) for (a, b) in edges_wanted if a in nodes and b in nodes]
    return nodes, edges, node_layer


def layered_layout(nodes: List[str], node_layer: Dict[str, str]) -> Dict[str, Tuple[float, float]]:
    """
    Deterministic layered layout (professional flow diagram).
    Layers go left -> right; nodes are stacked within each layer.
    """
    layer_order = ["Dev / Clients", "Workbench", "Services", "Execution", "Tool Runners", "Infra / Ops"]

    per_layer: Dict[str, List[str]] = {k: [] for k in layer_order}
    for n in nodes:
        per_layer.setdefault(node_layer.get(n, "Workbench"), []).append(n)

    # Fixed x positions for layers (columns)
    x_map = {layer: i * 3.1 for i, layer in enumerate(layer_order)}

    pos: Dict[str, Tuple[float, float]] = {}

    # y positions: stack nodes centered in each layer
    for layer in layer_order:
        items = per_layer.get(layer, [])
        if not items:
            continue

        step = 1.25
        total_height = (len(items) - 1) * step
        y0 = total_height / 2.0

        for idx, n in enumerate(items):
            x = x_map[layer]
            y = y0 - idx * step
            pos[n] = (x, y)

    return pos


def architecture_figure(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    project_totals: Dict[str, Totals],
    node_layer: Dict[str, str],
) -> go.Figure:
    """
    Professional architecture diagram:
      - Box nodes arranged in layers (left -> right)
      - Arrows indicating flow/dependency
      - Hover shows project stats (LOC/files)
    """
    pos = layered_layout(nodes, node_layer)

    # Node sizing reference
    codes = [project_totals.get(n, Totals()).code for n in nodes]
    max_code = max(codes) if codes else 1

    # Box dimensions (plot coords)
    box_w = 1.45
    box_h = 0.62

    def box_fill(layer: str) -> str:
        # Soft layer tints (kept subtle)
        if layer == "Dev / Clients":
            return "rgba(232, 244, 255, 0.95)"
        if layer == "Workbench":
            return "rgba(236, 255, 244, 0.95)"
        if layer == "Services":
            return "rgba(255, 246, 230, 0.95)"
        if layer == "Execution":
            return "rgba(255, 235, 238, 0.95)"
        if layer == "Tool Runners":
            return "rgba(245, 239, 255, 0.95)"
        return "rgba(245, 245, 245, 0.95)"  # Infra / Ops

    def loc_badge(code_lines: int) -> str:
        return f"{fmt_int(code_lines)} LOC"

    shapes: List[dict] = []
    annotations: List[dict] = []

    # Node boxes + labels
    for n in nodes:
        x, y = pos[n]
        t = project_totals.get(n, Totals())
        layer = node_layer.get(n, "")

        # Box
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=x - box_w / 2,
                x1=x + box_w / 2,
                y0=y - box_h / 2,
                y1=y + box_h / 2,
                line=dict(width=1),
                fillcolor=box_fill(layer),
                layer="below",
            )
        )

        # Main title
        annotations.append(
            dict(
                x=x,
                y=y + 0.08,
                xref="x",
                yref="y",
                text=f"<b>{n}</b>",
                showarrow=False,
                font=dict(size=12),
            )
        )

        # LOC line
        annotations.append(
            dict(
                x=x,
                y=y - 0.20,
                xref="x",
                yref="y",
                text=loc_badge(t.code),
                showarrow=False,
                font=dict(size=10, color="#555"),
            )
        )

    # Layer headings
    layer_order = ["Dev / Clients", "Workbench", "Services", "Execution", "Tool Runners", "Infra / Ops"]
    used_layers = [l for l in layer_order if any(node_layer.get(n) == l for n in nodes)]
    y_top = max(pos[n][1] for n in nodes) + 1.15 if nodes else 2.0

    for layer_name in used_layers:
        xs = [pos[n][0] for n in nodes if node_layer.get(n) == layer_name]
        if not xs:
            continue
        x = sum(xs) / len(xs)
        annotations.append(
            dict(
                x=x,
                y=y_top,
                xref="x",
                yref="y",
                text=f"<b>{layer_name}</b>",
                showarrow=False,
                font=dict(size=13),
            )
        )

    # Edges as arrows (annotations)
    edge_annotations: List[dict] = []
    for a, b in edges:
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_annotations.append(
            dict(
                x=x1 - box_w / 2,
                y=y1,
                ax=x0 + box_w / 2,
                ay=y0,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.0,
                arrowwidth=1,
                opacity=0.85,
                text="",
            )
        )

    # Invisible scatter points to enable hover tooltips (since shapes don't hover)
    node_x = []
    node_y = []
    hover_text = []
    for n in nodes:
        t = project_totals.get(n, Totals())
        hover_text.append(
            f"<b>{n}</b><br>"
            f"Layer: {node_layer.get(n,'')}<br>"
            f"Files: {fmt_int(t.files)}<br>"
            f"Blank: {fmt_int(t.blank)}<br>"
            f"Comment: {fmt_int(t.comment)}<br>"
            f"Code: {fmt_int(t.code)}"
        )
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])

    fig = go.Figure(
        data=[
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers",
                marker=dict(size=18, opacity=0.01),
                hovertext=hover_text,
                hoverinfo="text",
                showlegend=False,
            )
        ]
    )

    fig.update_layout(
        title="Architecture (professional flow) — layered platform view",
        shapes=shapes,
        annotations=annotations + edge_annotations,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=70, b=20),
        height=600,
    )
    return fig


# ------------------------------------------------------------------------------
# Charts + tables
# ------------------------------------------------------------------------------
def pie_figure(labels: List[str], values: List[int], title: str) -> go.Figure:
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.35)])
    fig.update_layout(title=title, height=420, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def bar_figure(x: List[str], y: List[int], title: str, ytitle: str = "Code lines") -> go.Figure:
    fig = go.Figure(data=[go.Bar(x=x, y=y)])
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title=ytitle,
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def table_figure(rows: List[Dict[str, Union[str, int, float]]], title: str) -> go.Figure:
    if not rows:
        return go.Figure()

    cols = list(rows[0].keys())
    values = [[r[c] for r in rows] for c in cols]

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(values=[f"<b>{c}</b>" for c in cols], align="left"),
                cells=dict(values=values, align="left"),
            )
        ]
    )
    fig.update_layout(title=title, height=420, margin=dict(l=20, r=20, t=60, b=20))
    return fig


# ------------------------------------------------------------------------------
# Report composer
# ------------------------------------------------------------------------------
def build_report(
    out_html: Path,
    title: str,
    timestamp: str,
    grand: Totals,
    project_totals: Dict[str, Totals],
    language_totals: Dict[str, Totals],
) -> None:
    proj_sorted = sorted(project_totals.items(), key=lambda kv: kv[1].code, reverse=True)
    proj_labels = [k for k, _ in proj_sorted]
    proj_values = [v.code for _, v in proj_sorted]

    lang_sorted = sorted(language_totals.items(), key=lambda kv: kv[1].code, reverse=True)
    lang_labels = [k for k, _ in lang_sorted]
    lang_values = [v.code for _, v in lang_sorted]

    nodes, edges, node_layer = build_architecture_spec(existing_projects=list(project_totals.keys()))
    fig_arch = architecture_figure(nodes, edges, project_totals, node_layer)

    fig_proj_pie = pie_figure(proj_labels, proj_values, "Project contribution (by code lines)")
    fig_proj_bar = bar_figure(proj_labels, proj_values, "Project contribution (bar)", "Code lines")

    fig_lang_pie = pie_figure(lang_labels[:14], lang_values[:14], "Top languages (by code lines)")
    fig_lang_bar = bar_figure(lang_labels[:20], lang_values[:20], "Top languages (bar)", "Code lines")

    proj_rows: List[Dict[str, Union[str, int, float]]] = []
    for name, t in proj_sorted:
        proj_rows.append(
            {
                "Project": name,
                "Files": t.files,
                "Blank": t.blank,
                "Comment": t.comment,
                "Code": t.code,
                "Code %": round(100.0 * safe_div(t.code, grand.code), 2),
            }
        )
    fig_proj_table = table_figure(proj_rows, "Per-project totals")

    lang_rows: List[Dict[str, Union[str, int, float]]] = []
    for name, t in lang_sorted:
        lang_rows.append(
            {
                "Language": name,
                "Files": t.files,
                "Blank": t.blank,
                "Comment": t.comment,
                "Code": t.code,
                "Code %": round(100.0 * safe_div(t.code, grand.code), 2),
            }
        )
    fig_lang_table = table_figure(lang_rows, "Language totals (overall)")

    out_html.parent.mkdir(parents=True, exist_ok=True)

    summary_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 1200px; margin: 18px auto;">
      <h1 style="margin-bottom: 6px;">{title}</h1>
      <div style="color: #555; margin-bottom: 16px;">
        <div><b>Generated:</b> {timestamp}</div>
        <div><b>Grand total:</b> Files {fmt_int(grand.files)} · Blank {fmt_int(grand.blank)} · Comment {fmt_int(grand.comment)} · Code {fmt_int(grand.code)}</div>
      </div>
      <hr/>
      <h2>Architecture</h2>
      <p style="color:#555; margin-top: -6px;">
        Professional layered flow diagram. Hover components for metrics.
      </p>
    </div>
    """

    # Include plotly.js once via CDN (keeps report small).
    # If you want fully portable/offline: change to include_plotlyjs="inline"
    arch_html = fig_arch.to_html(full_html=False, include_plotlyjs="cdn")
    proj_pie_html = fig_proj_pie.to_html(full_html=False, include_plotlyjs=False)
    proj_bar_html = fig_proj_bar.to_html(full_html=False, include_plotlyjs=False)
    lang_pie_html = fig_lang_pie.to_html(full_html=False, include_plotlyjs=False)
    lang_bar_html = fig_lang_bar.to_html(full_html=False, include_plotlyjs=False)
    proj_table_html = fig_proj_table.to_html(full_html=False, include_plotlyjs=False)
    lang_table_html = fig_lang_table.to_html(full_html=False, include_plotlyjs=False)

    sections_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 1200px; margin: 18px auto;">
      {arch_html}
      <hr style="margin: 22px 0;"/>

      <h2>Project contributions</h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px;">
        <div>{proj_pie_html}</div>
        <div>{proj_bar_html}</div>
      </div>
      <div style="margin-top: 14px;">{proj_table_html}</div>

      <hr style="margin: 22px 0;"/>

      <h2>Language contributions (overall)</h2>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px;">
        <div>{lang_pie_html}</div>
        <div>{lang_bar_html}</div>
      </div>
      <div style="margin-top: 14px;">{lang_table_html}</div>

      <hr style="margin: 22px 0;"/>
      <div style="color:#777; font-size: 12px;">
        Notes: counts exclude vendored/runtime dirs and selected file extensions per your cloc policy.
      </div>
    </div>
    """

    full_html = (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        "</head><body>"
        f"{summary_html}{sections_html}"
        "</body></html>"
    )
    out_html.write_text(full_html, encoding="utf-8")


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main() -> int:
    ensure_cloc()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = "OmniBioAI Platform — Architecture + Codebase Statistics (Interactive)"

    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    else:
        targets = [
            Path("omnibioai-tool-exec"),
            Path("omnibioai"),
            Path("ragbio"),
            Path("lims-x"),
            Path("omnibioai-toolserver"),
            Path("aws-tools"),
            Path("db-init"),
            Path("ai-dev-docker"),
            Path("k8s"),
            Path("docker-compose.yml"),
            Path("start_stack_tmux.sh"),
            Path("smoke_test_stack.sh"),
            Path("omnibioai_sdk"),
        ]

    validate_paths(targets)

    project_totals: Dict[str, Totals] = {}
    language_totals: Dict[str, Totals] = {}
    grand = Totals()

    for t in targets:
        overall, per_lang = run_cloc(t)

        key = str(t)
        project_totals[key] = overall
        grand.add(overall)

        for lang, tot in per_lang.items():
            language_totals.setdefault(lang, Totals()).add(tot)

    out_html = Path("out/reports/omnibioai_codebase_report.html")
    build_report(
        out_html=out_html,
        title=title,
        timestamp=ts,
        grand=grand,
        project_totals=project_totals,
        language_totals=language_totals,
    )

    print(f"\nOK: wrote interactive report: {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
