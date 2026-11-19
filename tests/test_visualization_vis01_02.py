import json
import xml.etree.ElementTree as ET
from pathlib import Path

from sipl.cli import EXIT_OK, main
from sipl.parser import parse, parse_to_concrete_tree
from sipl.visualization import (
    ast_to_vis,
    parse_tree_to_vis,
    render_comparison_html,
    render_dot,
    render_json,
    render_svg,
    render_text,
    tree_metrics,
)

ROOT = Path(__file__).resolve().parent.parent
POSITIVE_DIR = ROOT / "examples" / "positive"


def test_parse_tree_vis_all_formats_and_fragments() -> None:
    src = (POSITIVE_DIR / "01_gcd.sipl").read_text(encoding="utf-8")
    tree = parse_to_concrete_tree(src, filename="01_gcd.sipl")
    vis = parse_tree_to_vis(tree, src, filename="01_gcd.sipl")

    text_out = render_text(vis)
    assert "<program>" in text_out
    assert "while" in text_out

    json_data = json.loads(render_json(vis))
    assert json_data["label"] == "<program>"
    assert json_data["span"]["file"] == "01_gcd.sipl"
    assert len(json_data["children"]) == 3  # begin, stmt, end

    dot_out = render_dot(vis, title="GCD Parse Tree")
    assert dot_out.startswith('digraph "GCD Parse Tree"')
    assert "->" in dot_out

    svg_out = render_svg(vis, title="GCD Parse Tree")
    root_xml = ET.fromstring(svg_out)
    assert root_xml.tag.endswith("svg")


def test_ast_vis_and_comparison_metrics() -> None:
    src = (POSITIVE_DIR / "02_power.sipl").read_text(encoding="utf-8")
    pt = parse_tree_to_vis(parse_to_concrete_tree(src, "02_power.sipl"), src, "02_power.sipl")
    ast = ast_to_vis(parse(src, "02_power.sipl"), src)

    pt_m = tree_metrics(pt)
    ast_m = tree_metrics(ast)
    # Конкретне дерево завжди містить більше вузлів через токени-роздільники
    assert pt_m["nodes"] > ast_m["nodes"]

    html_out = render_comparison_html(src, pt, ast, filename="02_power.sipl")
    assert "<!DOCTYPE html>" in html_out
    assert "Parse Tree" in html_out
    assert "AST" in html_out
    assert 'data-span="' in html_out


def test_cli_visualization_commands(tmp_path: Path) -> None:
    gcd = str(POSITIVE_DIR / "01_gcd.sipl")
    svg_file = tmp_path / "pt.svg"
    dot_file = tmp_path / "ast.dot"
    html_file = tmp_path / "compare.html"

    assert main(["vis-tree", gcd, "--format", "svg", "-o", str(svg_file)]) == EXIT_OK
    assert svg_file.is_file()
    assert "<svg" in svg_file.read_text(encoding="utf-8")

    assert main(["vis-ast", gcd, "--format", "dot", "-o", str(dot_file)]) == EXIT_OK
    assert dot_file.is_file()
    assert "digraph" in dot_file.read_text(encoding="utf-8")

    assert main(["vis-compare", gcd, "-o", str(html_file)]) == EXIT_OK
    assert html_file.is_file()
    assert "<!DOCTYPE html>" in html_file.read_text(encoding="utf-8")