"""Renderers for SIPL Parse Tree and AST (Text, JSON, DOT, SVG, and HTML comparison)."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any

from sipl.ast import SourceSpan
from sipl.visualization.models import VisNode, tree_metrics


def _fmt_span(span: SourceSpan) -> str:
    return f"{span.start_line}:{span.start_col}-{span.end_line}:{span.end_col}"


def render_text(root: VisNode) -> str:
    """Render a VisNode tree as an indented Unicode text tree with source fragments."""
    lines: list[str] = []

    def walk(node: VisNode, prefix: str, is_last: bool, is_root: bool) -> None:
        frag_part = f" | {node.fragment!r}" if node.fragment else ""
        info = f"{node.label} [{_fmt_span(node.span)}]{frag_part}"
        if is_root:
            lines.append(info)
            child_prefix = ""
        else:
            branch = "└── " if is_last else "├── "
            lines.append(f"{prefix}{branch}{info}")
            child_prefix = prefix + ("    " if is_last else "│   ")

        for idx, child in enumerate(node.children):
            walk(child, child_prefix, idx == len(node.children) - 1, is_root=False)

    walk(root, "", True, is_root=True)
    return "\n".join(lines)


def render_json(root: VisNode) -> str:
    """Render a VisNode tree as formatted JSON."""
    return json.dumps(root.to_dict(), ensure_ascii=False, indent=2)


def render_dot(root: VisNode, title: str = "SIPL Tree") -> str:
    """Render a VisNode tree in Graphviz DOT format."""
    lines = [
        f'digraph "{title}" {{',
        '  node [fontname="Consolas", fontsize=10];',
        "  rankdir=TB;",
    ]

    def escape_dot(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def walk(node: VisNode) -> None:
        span_str = _fmt_span(node.span)
        label = escape_dot(f"{node.label}\n[{span_str}]")
        tooltip = escape_dot(f"{span_str}: {node.fragment}")
        if node.kind == "token":
            style = f'shape=ellipse, style=filled, fillcolor="#e8f5e9", label="{label}"'
        elif node.kind == "rule":
            style = f'shape=box, style="rounded,filled", fillcolor="#e3f2fd", label="{label}"'
        else:
            style = f'shape=box, style="rounded,filled", fillcolor="#fff3e0", label="{label}"'
        lines.append(f'  {node.id} [{style}, tooltip="{tooltip}"];')
        for child in node.children:
            lines.append(f"  {node.id} -> {child.id};")
            walk(child)

    walk(root)
    lines.append("}")
    return "\n".join(lines)


@dataclass
class _LayoutNode:
    vis: VisNode
    w: float
    h: float
    subtree_w: float
    x: float
    y: float
    children: list[_LayoutNode]


def _box_width(vis: VisNode) -> float:
    return max(76.0, min(190.0, len(vis.label) * 7.2 + 22.0))


def _layout_tree(
    root: VisNode,
    box_h: float = 36.0,
    h_gap: float = 14.0,
    v_gap: float = 42.0,
    padding: float = 20.0,
) -> tuple[_LayoutNode, float, float]:
    def measure(node: VisNode) -> _LayoutNode:
        w = _box_width(node)
        laid_children = [measure(ch) for ch in node.children]
        if laid_children:
            children_w = sum(c.subtree_w for c in laid_children) + h_gap * (len(laid_children) - 1)
        else:
            children_w = 0.0
        subtree_w = max(w, children_w)
        return _LayoutNode(
            vis=node,
            w=w,
            h=box_h,
            subtree_w=subtree_w,
            x=0.0,
            y=0.0,
            children=laid_children,
        )

    max_depth = 0

    def place(node: _LayoutNode, left_x: float, depth: int) -> None:
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        node.x = left_x + node.subtree_w / 2.0
        node.y = padding + depth * (box_h + v_gap)
        if not node.children:
            return
        children_w = sum(c.subtree_w for c in node.children) + h_gap * (len(node.children) - 1)
        cur_x = left_x + (node.subtree_w - children_w) / 2.0
        for child in node.children:
            place(child, cur_x, depth + 1)
            cur_x += child.subtree_w + h_gap

    measured = measure(root)
    place(measured, padding, 0)
    total_w = measured.subtree_w + 2 * padding
    total_h = (max_depth + 1) * box_h + max_depth * v_gap + 2 * padding
    return measured, total_w, total_h


def _render_svg_inner(root: VisNode, interactive: bool = False) -> tuple[str, float, float]:
    layout, width, height = _layout_tree(root)
    edges: list[str] = []
    nodes_svg: list[str] = []

    def walk(node: _LayoutNode) -> None:
        x1 = node.x
        y1 = node.y + node.h
        for child in node.children:
            x2 = child.x
            y2 = child.y
            edges.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#64748b" stroke-width="1.5" />'
            )
            walk(child)

        vis = node.vis
        if vis.kind == "token":
            fill, stroke = "#dcfce7", "#16a34a"
        elif vis.kind == "rule":
            fill, stroke = "#dbeafe", "#2563eb"
        else:
            fill, stroke = "#ffedd5", "#ea580c"

        rx = node.x - node.w / 2.0
        ry = node.y
        span = vis.span
        span_key = _fmt_span(span)
        label_esc = html.escape(vis.label)
        frag_esc = html.escape(vis.fragment)
        title_esc = html.escape(f"{vis.label} [{span_key}] -> {vis.fragment}")

        attrs = ""
        if interactive:
            attrs = (
                f' class="vis-node" data-id="{html.escape(vis.id)}" '
                f'data-kind="{vis.kind}" data-span="{span_key}" '
                f'data-sl="{span.start_line}" data-sc="{span.start_col}" '
                f'data-el="{span.end_line}" data-ec="{span.end_col}" '
                f'data-label="{label_esc}" data-frag="{frag_esc}"'
            )

        nodes_svg.append(
            f"<g{attrs}>"
            f"<title>{title_esc}</title>"
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{node.w:.1f}" height="{node.h:.1f}" '
            f'rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.5" />'
            f'<text x="{node.x:.1f}" y="{ry + 22:.1f}" text-anchor="middle" '
            f'font-family="Consolas, monospace" font-size="11" fill="#0f172a">'
            f"{label_esc}</text>"
            f"</g>"
        )

    walk(layout)
    body = "\n".join(edges + nodes_svg)
    return body, width, height


def render_svg(root: VisNode, title: str = "SIPL Tree") -> str:
    """Render a VisNode tree as a standalone SVG image."""
    body, width, height = _render_svg_inner(root, interactive=False)
    title_esc = html.escape(title)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">\n'
        f"<title>{title_esc}</title>\n"
        f'<rect width="100%" height="100%" fill="#ffffff" />\n'
        f"{body}\n"
        f"</svg>"
    )


def render_comparison_html(
    source: str,
    parse_tree: VisNode,
    ast_tree: VisNode,
    filename: str = "<stdin>",
) -> str:
    """Render an interactive HTML page comparing Parse Tree and AST side by side."""
    pt_svg, pt_w, pt_h = _render_svg_inner(parse_tree, interactive=True)
    ast_svg, ast_w, ast_h = _render_svg_inner(ast_tree, interactive=True)
    pt_stats: dict[str, Any] = tree_metrics(parse_tree)
    ast_stats: dict[str, Any] = tree_metrics(ast_tree)

    code_lines_html: list[str] = []
    for idx, line_text in enumerate(source.splitlines() or [""], start=1):
        escaped_line = html.escape(line_text) if line_text else " "
        code_lines_html.append(
            f'<div class="code-line" data-line="{idx}">'
            f'<span class="ln">{idx}</span>'
            f'<span class="lc">{escaped_line}</span>'
            f"</div>"
        )
    code_block = "\n".join(code_lines_html)
    file_esc = html.escape(filename)

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8" />
  <title>SIPL Parse Tree vs AST — {file_esc}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }}
    header {{ padding: 14px 20px; background: #0f172a; color: #fff; }}
    header h1 {{ margin: 0 0 6px 0; font-size: 18px; }}
    .stats {{ font-size: 13px; color: #cbd5e1; }}
    .inspector {{ padding: 10px 20px; background: #e2e8f0; font-family: Consolas, monospace;
                  font-size: 13px; border-bottom: 1px solid #cbd5e1; }}
    .grid {{ display: grid; grid-template-columns: 320px 1fr 1fr; gap: 12px; padding: 12px;
             height: calc(100vh - 118px); box-sizing: border-box; }}
    .panel {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 8px;
              display: flex; flex-direction: column; overflow: hidden; }}
    .panel h2 {{ margin: 0; padding: 10px 12px; font-size: 14px; background: #f1f5f9;
                 border-bottom: 1px solid #cbd5e1; }}
    .scroll {{ overflow: auto; flex: 1; padding: 8px; }}
    .code-line {{ font-family: Consolas, monospace; font-size: 13px; white-space: pre;
                  padding: 2px 6px; border-radius: 4px; }}
    .code-line .ln {{ display: inline-block; width: 28px; color: #94a3b8; user-select: none; }}
    .code-line.active {{ background: #fef08a; }}
    .vis-node {{ cursor: pointer; }}
    .vis-node.selected rect {{ stroke: #dc2626 !important; stroke-width: 3px !important; }}
    .vis-node.matched rect {{ stroke: #7c3aed !important; stroke-width: 2.5px !important;
                              stroke-dasharray: 4 2; }}
  </style>
</head>
<body>
  <header>
    <h1>SIPL: Порівняння Parse Tree &harr; AST ({file_esc})</h1>
    <div class="stats">
      Parse Tree: {pt_stats["nodes"]} вузлів (глибина {pt_stats["depth"]}) &nbsp;|&nbsp;
      AST: {ast_stats["nodes"]} вузлів (глибина {ast_stats["depth"]}) &nbsp;|&nbsp;
      Натисніть на будь-який вузол для синхронізації з кодом та іншим деревом
    </div>
  </header>
  <div class="inspector" id="inspector">Виберіть вузол на Parse Tree або AST...</div>
  <div class="grid">
    <section class="panel">
      <h2>Вихідний код</h2>
      <div class="scroll">{code_block}</div>
    </section>
    <section class="panel">
      <h2>Конкретний синтаксис (Parse Tree)</h2>
      <div class="scroll">
        <svg width="{pt_w:.0f}" height="{pt_h:.0f}" viewBox="0 0 {pt_w:.0f} {pt_h:.0f}">
          {pt_svg}
        </svg>
      </div>
    </section>
    <section class="panel">
      <h2>Абстрактний синтаксис (AST)</h2>
      <div class="scroll">
        <svg width="{ast_w:.0f}" height="{ast_h:.0f}" viewBox="0 0 {ast_w:.0f} {ast_h:.0f}">
          {ast_svg}
        </svg>
      </div>
    </section>
  </div>
  <script>
    const nodes = Array.from(document.querySelectorAll('.vis-node'));
    const codeLines = Array.from(document.querySelectorAll('.code-line'));
    const inspector = document.getElementById('inspector');

    nodes.forEach(node => {{
      node.addEventListener('click', () => {{
        nodes.forEach(n => n.classList.remove('selected', 'matched'));
        codeLines.forEach(l => l.classList.remove('active'));

        node.classList.add('selected');
        const span = node.dataset.span;
        const sl = Number(node.dataset.sl);
        const el = Number(node.dataset.el);

        nodes.forEach(other => {{
          if (other !== node && other.dataset.span === span) {{
            other.classList.add('matched');
          }}
        }});

        codeLines.forEach(line => {{
          const ln = Number(line.dataset.line);
          if (ln >= sl && ln <= el) {{
            line.classList.add('active');
          }}
        }});

        inspector.textContent =
          `[${{node.dataset.kind}}] ${{node.dataset.label}} | ` +
          `span=${{span}} | fragment="${{node.dataset.frag}}"`;
      }});
    }});
  </script>
</body>
</html>
"""