"""SIPL parser producing both Lark parse trees and typed AST nodes."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from lark import (
    Lark,
    Token,
    Transformer,
    Tree,
    UnexpectedCharacters,
    UnexpectedEOF,
    UnexpectedInput,
    UnexpectedToken,
    v_args,
)
from lark.tree import Meta

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
from sipl.errors import SiplSyntaxError

_GRAMMAR_FILE = Path(__file__).resolve().parents[2] / "grammar" / "sipl.lark"


@lru_cache(maxsize=1)
def _get_lark_parser() -> Lark:
    grammar_text = _GRAMMAR_FILE.read_text(encoding="utf-8")
    return Lark(
        grammar_text,
        start="start",
        parser="earley",
        ambiguity="explicit",
        propagate_positions=True,
    )

@lru_cache(maxsize=1)
def _get_concrete_lark_parser() -> Lark:
    grammar_text = _GRAMMAR_FILE.read_text(encoding="utf-8")
    return Lark(
        grammar_text,
        start="start",
        parser="earley",
        ambiguity="explicit",
        propagate_positions=True,
        keep_all_tokens=True,
    )


def _span_from_meta(meta: Meta, filename: str) -> SourceSpan:
    if meta.empty:
        return SourceSpan(filename, 1, 1, 1, 1)
    return SourceSpan(
        file=filename,
        start_line=meta.line,
        start_col=meta.column,
        end_line=meta.end_line,
        end_col=meta.end_column,
    )


def _span_from_token(token: Token, filename: str) -> SourceSpan:
    return SourceSpan(
        file=filename,
        start_line=token.line or 1,
        start_col=token.column or 1,
        end_line=token.end_line or (token.line or 1),
        end_col=token.end_column or (token.column or 1),
    )


@v_args(meta=True)
class _SiplAstTransformer(Transformer[Token, Program]):
    """Transforms a Lark parse tree into typed SIPL AST nodes."""

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def start(self, meta: Meta, children: list[Any]) -> Program:
        program: Program = children[0]
        return program

    def program(self, meta: Meta, children: list[Any]) -> Program:
        body: Stmt = children[0]
        return Program(body=body, span=_span_from_meta(meta, self.filename))

    def seq(self, meta: Meta, children: list[Any]) -> SeqStmt:
        first: Stmt = children[0]
        second: Stmt = children[1]
        return SeqStmt(first=first, second=second, span=_span_from_meta(meta, self.filename))

    def assign(self, meta: Meta, children: list[Any]) -> AssignStmt:
        ident_tok: Token = children[0]
        value: AExp = children[1]
        return AssignStmt(
            target=str(ident_tok),
            target_span=_span_from_token(ident_tok, self.filename),
            value=value,
            span=_span_from_meta(meta, self.filename),
        )

    def if_stmt(self, meta: Meta, children: list[Any]) -> IfStmt:
        condition: BExp = children[0]
        then_branch: Stmt = children[1]
        else_branch: Stmt = children[2]
        return IfStmt(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            span=_span_from_meta(meta, self.filename),
        )

    def while_stmt(self, meta: Meta, children: list[Any]) -> WhileStmt:
        condition: BExp = children[0]
        body: Stmt = children[1]
        return WhileStmt(
            condition=condition,
            body=body,
            span=_span_from_meta(meta, self.filename),
        )

    def block(self, meta: Meta, children: list[Any]) -> BlockStmt:
        body: Stmt = children[0]
        return BlockStmt(body=body, span=_span_from_meta(meta, self.filename))

    def skip_stmt(self, meta: Meta, children: list[Any]) -> SkipStmt:
        return SkipStmt(span=_span_from_meta(meta, self.filename))

    def add(self, meta: Meta, children: list[Any]) -> BinaryArithExpr:
        left: AExp = children[0]
        right: AExp = children[1]
        return BinaryArithExpr(
            op="+",
            left=left,
            right=right,
            span=_span_from_meta(meta, self.filename),
        )

    def sub(self, meta: Meta, children: list[Any]) -> BinaryArithExpr:
        left: AExp = children[0]
        right: AExp = children[1]
        return BinaryArithExpr(
            op="-",
            left=left,
            right=right,
            span=_span_from_meta(meta, self.filename),
        )

    def mul(self, meta: Meta, children: list[Any]) -> BinaryArithExpr:
        left: AExp = children[0]
        right: AExp = children[1]
        return BinaryArithExpr(
            op="*",
            left=left,
            right=right,
            span=_span_from_meta(meta, self.filename),
        )

    def int_lit(self, meta: Meta, children: list[Any]) -> IntLiteral:
        num_tok: Token = children[0]
        return IntLiteral(value=int(num_tok), span=_span_from_meta(meta, self.filename))

    def neg_int_lit(self, meta: Meta, children: list[Any]) -> IntLiteral:
        num_tok: Token = children[0]
        return IntLiteral(value=-int(num_tok), span=_span_from_meta(meta, self.filename))

    def var_ref(self, meta: Meta, children: list[Any]) -> VarExpr:
        ident_tok: Token = children[0]
        return VarExpr(name=str(ident_tok), span=_span_from_meta(meta, self.filename))

    def or_expr(self, meta: Meta, children: list[Any]) -> OrExpr:
        left: BExp = children[0]
        right: BExp = children[2]
        return OrExpr(left=left, right=right, span=_span_from_meta(meta, self.filename))

    def not_expr(self, meta: Meta, children: list[Any]) -> NotExpr:
        operand: BExp = children[1]
        return NotExpr(operand=operand, span=_span_from_meta(meta, self.filename))

    def eq_expr(self, meta: Meta, children: list[Any]) -> CompareExpr:
        left: AExp = children[0]
        right: AExp = children[1]
        return CompareExpr(
            op="=",
            left=left,
            right=right,
            span=_span_from_meta(meta, self.filename),
        )

    def gt_expr(self, meta: Meta, children: list[Any]) -> CompareExpr:
        left: AExp = children[0]
        right: AExp = children[1]
        return CompareExpr(
            op=">",
            left=left,
            right=right,
            span=_span_from_meta(meta, self.filename),
        )


def _format_syntax_error(err: UnexpectedInput, source: str, filename: str) -> SiplSyntaxError:
    line = max(1, getattr(err, "line", 1) or 1)
    col = max(1, getattr(err, "column", 1) or 1)
    span = SourceSpan(file=filename, start_line=line, start_col=col, end_line=line, end_col=col + 1)
    snippet = err.get_context(source) if source else ""

    if isinstance(err, UnexpectedEOF):
        expected = ", ".join(sorted(err.expected)) if err.expected else "statement or 'end'"
        msg = f"Unexpected end of file; expected: {expected}"
    elif isinstance(err, UnexpectedCharacters):
        msg = f"Unexpected character {err.char!r} at line {line}, column {col}"
    elif isinstance(err, UnexpectedToken):
        expected = ", ".join(sorted(err.expected)) if err.expected else "valid syntax"
        msg = f"Unexpected token {str(err.token)!r}; expected: {expected}"
    else:
        msg = f"Syntax error at line {line}, column {col}"

    return SiplSyntaxError(message=msg, span=span, snippet=snippet)


def parse_to_parse_tree(source: str, filename: str = "<stdin>") -> Tree[Token]:
    """Parse SIPL source into a Lark parse tree with source positions."""
    parser = _get_lark_parser()
    try:
        tree = parser.parse(source)
    except UnexpectedInput as exc:
        raise _format_syntax_error(exc, source, filename) from exc
    return tree

def parse_to_concrete_tree(source: str, filename: str = "<stdin>") -> Tree[Token]:
    """Parse SIPL source into a concrete Lark parse tree keeping all tokens."""
    parser = _get_concrete_lark_parser()
    try:
        tree = parser.parse(source)
    except UnexpectedInput as exc:
        raise _format_syntax_error(exc, source, filename) from exc
    return tree

def parse(source: str, filename: str = "<stdin>") -> Program:
    """Parse SIPL source into a typed Program AST."""
    tree = parse_to_parse_tree(source, filename=filename)
    transformer = _SiplAstTransformer(filename=filename)
    return transformer.transform(tree)