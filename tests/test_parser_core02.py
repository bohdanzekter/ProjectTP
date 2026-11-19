from pathlib import Path

import pytest

from sipl.ast import (
    AssignStmt,
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
    VarExpr,
    WhileStmt,
)
from sipl.errors import SiplSyntaxError
from sipl.parser import parse

ROOT = Path(__file__).resolve().parent.parent
POSITIVE_DIR = ROOT / "examples" / "positive"
NEGATIVE_DIR = ROOT / "examples" / "negative"


def test_precedence_arith_and_left_assoc() -> None:
    prog = parse("begin A := X + Y * Z - 2 end", filename="arith.sipl")
    assert isinstance(prog, Program)
    assert isinstance(prog.body, AssignStmt)
    assert prog.body.target == "A"

    # (X + (Y * Z)) - 2
    expr = prog.body.value
    assert isinstance(expr, BinaryArithExpr)
    assert expr.op == "-"
    assert isinstance(expr.right, IntLiteral)
    assert expr.right.value == 2

    left_add = expr.left
    assert isinstance(left_add, BinaryArithExpr)
    assert left_add.op == "+"
    assert isinstance(left_add.left, VarExpr)
    assert left_add.left.name == "X"
    assert isinstance(left_add.right, BinaryArithExpr)
    assert left_add.right.op == "*"


def test_precedence_bool_not_before_or() -> None:
    prog = parse("begin if ¬M = N ∨ M > N then skip else skip end")
    assert isinstance(prog.body, IfStmt)
    cond = prog.body.condition
    # (¬(M = N)) ∨ (M > N)
    assert isinstance(cond, OrExpr)
    assert isinstance(cond.left, NotExpr)
    assert isinstance(cond.left.operand, CompareExpr)
    assert cond.left.operand.op == "="
    assert isinstance(cond.right, CompareExpr)
    assert cond.right.op == ">"


def test_precedence_seq_lower_than_while_and_if() -> None:
    prog = parse("begin while Y > 0 do Y := Y - 1; X := 10 end")
    assert isinstance(prog.body, SeqStmt)
    assert isinstance(prog.body.first, WhileStmt)
    assert isinstance(prog.body.second, AssignStmt)
    assert prog.body.second.target == "X"

    prog2 = parse("begin if X > 0 then skip else Y := 1; Z := 2 end")
    assert isinstance(prog2.body, SeqStmt)
    assert isinstance(prog2.body.first, IfStmt)
    assert isinstance(prog2.body.second, AssignStmt)
    assert prog2.body.second.target == "Z"


def test_source_spans_are_populated() -> None:
    code = "begin\n  X := -5;\n  begin\n    skip\n  end\nend\n"
    prog = parse(code, filename="test.sipl")
    assert prog.span.file == "test.sipl"
    assert prog.span.start_line == 1
    assert prog.span.end_line == 6

    assert isinstance(prog.body, SeqStmt)
    assign = prog.body.first
    assert isinstance(assign, AssignStmt)
    assert assign.span.start_line == 2
    assert assign.target_span.start_line == 2
    assert assign.target_span.start_col == 3
    assert isinstance(assign.value, IntLiteral)
    assert assign.value.value == -5

    block = prog.body.second
    assert isinstance(block, BlockStmt)
    assert isinstance(block.body, SkipStmt)
    assert block.body.span.start_line == 4


@pytest.mark.parametrize("path", sorted(POSITIVE_DIR.glob("*.sipl")), ids=lambda p: p.name)
def test_all_positive_examples_build_typed_ast(path: Path) -> None:
    prog = parse(path.read_text(encoding="utf-8"), filename=path.name)
    assert isinstance(prog, Program)
    data = prog.to_dict()
    assert data["type"] == "Program"


@pytest.mark.parametrize("path", sorted(NEGATIVE_DIR.glob("*.sipl")), ids=lambda p: p.name)
def test_all_negative_examples_raise_sipl_syntax_error(path: Path) -> None:
    with pytest.raises(SiplSyntaxError) as exc_info:
        parse(path.read_text(encoding="utf-8"), filename=path.name)
    err = exc_info.value
    assert err.span is not None
    assert err.span.file == path.name
    assert err.span.start_line >= 1
    assert err.span.start_col >= 1
    assert len(err.message) > 0