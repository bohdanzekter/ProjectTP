"""Typed AST nodes and source span definitions for SIPL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class SourceSpan:
    """Position of a syntax construct in source text (1-based lines and columns)."""

    file: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }


# --- Arithmetic expressions (Aexp) ---


@dataclass(frozen=True)
class IntLiteral:
    value: int
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {"type": "IntLiteral", "value": self.value, "span": self.span.to_dict()}


@dataclass(frozen=True)
class VarExpr:
    name: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {"type": "VarExpr", "name": self.name, "span": self.span.to_dict()}


@dataclass(frozen=True)
class BinaryArithExpr:
    op: Literal["+", "-", "*"]
    left: AExp
    right: AExp
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "BinaryArithExpr",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_dict(),
        }


AExp = IntLiteral | VarExpr | BinaryArithExpr


# --- Boolean expressions / conditions (Bexp) ---


@dataclass(frozen=True)
class CompareExpr:
    op: Literal["=", ">"]
    left: AExp
    right: AExp
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "CompareExpr",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class NotExpr:
    operand: BExp
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "NotExpr",
            "operand": self.operand.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class OrExpr:
    left: BExp
    right: BExp
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "OrExpr",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_dict(),
        }


BExp = CompareExpr | NotExpr | OrExpr


# --- Statements (Stm) ---


@dataclass(frozen=True)
class AssignStmt:
    target: str
    target_span: SourceSpan
    value: AExp
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "AssignStmt",
            "target": self.target,
            "target_span": self.target_span.to_dict(),
            "value": self.value.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class SeqStmt:
    first: Stmt
    second: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "SeqStmt",
            "first": self.first.to_dict(),
            "second": self.second.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class IfStmt:
    condition: BExp
    then_branch: Stmt
    else_branch: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "IfStmt",
            "condition": self.condition.to_dict(),
            "then_branch": self.then_branch.to_dict(),
            "else_branch": self.else_branch.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class WhileStmt:
    condition: BExp
    body: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "WhileStmt",
            "condition": self.condition.to_dict(),
            "body": self.body.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class BlockStmt:
    body: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "BlockStmt",
            "body": self.body.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class SkipStmt:
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {"type": "SkipStmt", "span": self.span.to_dict()}


Stmt = AssignStmt | SeqStmt | IfStmt | WhileStmt | BlockStmt | SkipStmt


@dataclass(frozen=True)
class Program:
    body: Stmt
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "Program",
            "body": self.body.to_dict(),
            "span": self.span.to_dict(),
        }