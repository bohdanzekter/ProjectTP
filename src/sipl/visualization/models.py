"""Unified tree model linking Parse Tree and AST nodes to source fragments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from lark import Token, Tree

from sipl.ast import (
    AExp,
    AssignStmt,
    BExp,
    BinaryArithExpr,
    BlockStmt,
    CompareExpr,
    IfStmt,
    IntLiteral,
    NotExpr,
    OrExpr,
    Program,
    SeqStmt,
    SkipStmt,
    SourceSpan,
    Stmt,
    VarExpr,
    WhileStmt,
)


@dataclass(frozen=True)
class VisNode:
    """Visualization node for either a concrete Parse Tree or an AST."""

    id: str
    label: str
    kind: Literal["rule", "token", "ast"]
    span: SourceSpan
    fragment: str
    children: list[VisNode]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "span": self.span.to_dict(),
            "fragment": self.fragment,
            "children": [c.to_dict() for c in self.children],
        }


def extract_fragment(source: str, span: SourceSpan) -> str:
    """Slice the exact source code fragment covered by a 1-based SourceSpan."""
    if not source:
        return ""
    lines = source.splitlines(keepends=True)
    if not lines:
        return ""

    s_line = max(1, min(span.start_line, len(lines)))
    e_line = max(s_line, min(span.end_line, len(lines)))
    s_col = max(1, span.start_col)
    e_col = max(1, span.end_col)

    if s_line == e_line:
        return lines[s_line - 1][s_col - 1 : e_col - 1].strip()

    parts = [lines[s_line - 1][s_col - 1 :]]
    for idx in range(s_line, e_line - 1):
        parts.append(lines[idx])
    parts.append(lines[e_line - 1][: e_col - 1])
    return "".join(parts).strip()


def _compact_fragment(text: str, limit: int = 36) -> str:
    single = " ".join(text.split())
    if len(single) <= limit:
        return single
    return single[: limit - 3] + "..."


class _IdCounter:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.value = 0

    def next(self) -> str:
        self.value += 1
        return f"{self.prefix}{self.value}"


def parse_tree_to_vis(tree: Tree[Token], source: str, filename: str = "<stdin>") -> VisNode:
    """Convert a Lark concrete parse tree into a VisNode hierarchy."""
    if tree.data == "start" and len(tree.children) == 1 and isinstance(tree.children[0], Tree):
        tree = tree.children[0]
    counter = _IdCounter("pt_")

    def visit(node: Tree[Token] | Token) -> VisNode:
        if isinstance(node, Token):
            span = SourceSpan(
                file=filename,
                start_line=node.line or 1,
                start_col=node.column or 1,
                end_line=node.end_line or (node.line or 1),
                end_col=node.end_column or (node.column or 1),
            )
            frag = str(node)
            if node.type in {"IDENT", "NUMBER"}:
                label = f"<{node.type}> {frag}"
            else:
                label = frag
            return VisNode(
                id=counter.next(),
                label=label,
                kind="token",
                span=span,
                fragment=frag,
                children=[],
            )

        meta = node.meta
        if meta.empty:
            span = SourceSpan(filename, 1, 1, 1, 1)
            frag = ""
        else:
            span = SourceSpan(
                file=filename,
                start_line=meta.line,
                start_col=meta.column,
                end_line=meta.end_line,
                end_col=meta.end_column,
            )
            if meta.start_pos is not None and meta.end_pos is not None:
                frag = _compact_fragment(source[meta.start_pos : meta.end_pos])
            else:
                frag = _compact_fragment(extract_fragment(source, span))

        children = [visit(ch) for ch in node.children]
        return VisNode(
            id=counter.next(),
            label=f"<{node.data}>",
            kind="rule",
            span=span,
            fragment=frag,
            children=children,
        )

    return visit(tree)


def ast_to_vis(program: Program, source: str) -> VisNode:
    """Convert a typed SIPL Program AST into a VisNode hierarchy."""
    counter = _IdCounter("ast_")

    def frag_of(span: SourceSpan) -> str:
        return _compact_fragment(extract_fragment(source, span))

    def visit_aexp(expr: AExp) -> VisNode:
        if isinstance(expr, IntLiteral):
            return VisNode(
                id=counter.next(),
                label=f"Int({expr.value})",
                kind="ast",
                span=expr.span,
                fragment=frag_of(expr.span),
                children=[],
            )
        if isinstance(expr, VarExpr):
            return VisNode(
                id=counter.next(),
                label=f"Var({expr.name})",
                kind="ast",
                span=expr.span,
                fragment=frag_of(expr.span),
                children=[],
            )
        if isinstance(expr, BinaryArithExpr):
            return VisNode(
                id=counter.next(),
                label=f"BinOp({expr.op})",
                kind="ast",
                span=expr.span,
                fragment=frag_of(expr.span),
                children=[visit_aexp(expr.left), visit_aexp(expr.right)],
            )
        raise TypeError(f"Unsupported AExp: {type(expr).__name__}")

    def visit_bexp(expr: BExp) -> VisNode:
        if isinstance(expr, CompareExpr):
            return VisNode(
                id=counter.next(),
                label=f"Cmp({expr.op})",
                kind="ast",
                span=expr.span,
                fragment=frag_of(expr.span),
                children=[visit_aexp(expr.left), visit_aexp(expr.right)],
            )
        if isinstance(expr, NotExpr):
            return VisNode(
                id=counter.next(),
                label="Not(¬)",
                kind="ast",
                span=expr.span,
                fragment=frag_of(expr.span),
                children=[visit_bexp(expr.operand)],
            )
        if isinstance(expr, OrExpr):
            return VisNode(
                id=counter.next(),
                label="Or(∨)",
                kind="ast",
                span=expr.span,
                fragment=frag_of(expr.span),
                children=[visit_bexp(expr.left), visit_bexp(expr.right)],
            )
        raise TypeError(f"Unsupported BExp: {type(expr).__name__}")

    def visit_stmt(stmt: Stmt) -> VisNode:
        if isinstance(stmt, AssignStmt):
            target_node = VisNode(
                id=counter.next(),
                label=f"Target({stmt.target})",
                kind="ast",
                span=stmt.target_span,
                fragment=frag_of(stmt.target_span),
                children=[],
            )
            return VisNode(
                id=counter.next(),
                label="Assign(:=)",
                kind="ast",
                span=stmt.span,
                fragment=frag_of(stmt.span),
                children=[target_node, visit_aexp(stmt.value)],
            )
        if isinstance(stmt, SeqStmt):
            return VisNode(
                id=counter.next(),
                label="Seq(;)",
                kind="ast",
                span=stmt.span,
                fragment=frag_of(stmt.span),
                children=[visit_stmt(stmt.first), visit_stmt(stmt.second)],
            )
        if isinstance(stmt, IfStmt):
            return VisNode(
                id=counter.next(),
                label="If",
                kind="ast",
                span=stmt.span,
                fragment=frag_of(stmt.span),
                children=[
                    visit_bexp(stmt.condition),
                    visit_stmt(stmt.then_branch),
                    visit_stmt(stmt.else_branch),
                ],
            )
        if isinstance(stmt, WhileStmt):
            return VisNode(
                id=counter.next(),
                label="While",
                kind="ast",
                span=stmt.span,
                fragment=frag_of(stmt.span),
                children=[visit_bexp(stmt.condition), visit_stmt(stmt.body)],
            )
        if isinstance(stmt, BlockStmt):
            return VisNode(
                id=counter.next(),
                label="Block",
                kind="ast",
                span=stmt.span,
                fragment=frag_of(stmt.span),
                children=[visit_stmt(stmt.body)],
            )
        if isinstance(stmt, SkipStmt):
            return VisNode(
                id=counter.next(),
                label="Skip",
                kind="ast",
                span=stmt.span,
                fragment=frag_of(stmt.span),
                children=[],
            )
        raise TypeError(f"Unsupported Stmt: {type(stmt).__name__}")

    return VisNode(
        id=counter.next(),
        label="Program",
        kind="ast",
        span=program.span,
        fragment=frag_of(program.span),
        children=[visit_stmt(program.body)],
    )


def tree_metrics(root: VisNode) -> dict[str, int]:
    """Compute node count, leaf count, and height of a VisNode tree."""
    nodes = 0
    leaves = 0

    def walk(node: VisNode) -> int:
        nonlocal nodes, leaves
        nodes += 1
        if not node.children:
            leaves += 1
            return 1
        return 1 + max(walk(ch) for ch in node.children)

    depth = walk(root)
    return {"nodes": nodes, "leaves": leaves, "depth": depth}