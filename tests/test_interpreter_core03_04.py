from pathlib import Path

import pytest

from sipl.errors import StepLimitExceededError, UndefinedVariableError
from sipl.interpreter import (
    BeforeStatementEvent,
    ConditionEvaluatedEvent,
    ExecutionErrorEvent,
    ExecutionFinishedEvent,
    Interpreter,
    State,
    TraceEvent,
    VariableChangedEvent,
)
from sipl.parser import parse

ROOT = Path(__file__).resolve().parent.parent
POSITIVE_DIR = ROOT / "examples" / "positive"


def test_gcd_example() -> None:
    src = (POSITIVE_DIR / "01_gcd.sipl").read_text(encoding="utf-8")
    prog = parse(src, filename="01_gcd.sipl")
    result = Interpreter().run(prog, initial_state={"M": 8, "N": 16})
    assert result.final_state == State({"M": 8, "N": 8})
    assert result.steps > 0


def test_power_example() -> None:
    src = (POSITIVE_DIR / "02_power.sipl").read_text(encoding="utf-8")
    prog = parse(src, filename="02_power.sipl")
    result = Interpreter().run(prog, initial_state={"X": 5, "Y": 2})
    assert result.final_state.get("R") == 25
    assert result.final_state.get("Y") == 0


def test_div_example() -> None:
    src = (POSITIVE_DIR / "03_div.sipl").read_text(encoding="utf-8")
    prog = parse(src, filename="03_div.sipl")
    result = Interpreter().run(prog, initial_state={"X": 7, "Y": 4})
    assert result.final_state.get("R") == 1
    assert result.final_state.get("X") == 3


def test_factorial_example() -> None:
    src = (POSITIVE_DIR / "10_factorial.sipl").read_text(encoding="utf-8")
    prog = parse(src, filename="10_factorial.sipl")
    result = Interpreter().run(prog, initial_state={"N": 5})
    assert result.final_state.get("F") == 120


def test_skip_and_nested_blocks_and_negatives() -> None:
    src_skip = (POSITIVE_DIR / "04_skip.sipl").read_text(encoding="utf-8")
    res_skip = Interpreter().run(parse(src_skip))
    assert res_skip.final_state == State({})

    src_nested = (POSITIVE_DIR / "05_nested_blocks.sipl").read_text(encoding="utf-8")
    res_nested = Interpreter().run(parse(src_nested))
    assert res_nested.final_state == State({"X": 1, "Y": 3, "Z": 9})

    src_neg = (POSITIVE_DIR / "09_negative_numbers.sipl").read_text(encoding="utf-8")
    res_neg = Interpreter().run(parse(src_neg))
    assert res_neg.final_state == State({"X": -5, "Y": -8, "Z": -4})


def test_if_branches_and_boolean_operators() -> None:
    src = (POSITIVE_DIR / "07_precedence_bool.sipl").read_text(encoding="utf-8")
    prog = parse(src)
    res_true = Interpreter().run(prog, initial_state={"A": 2, "B": 5})
    assert res_true.final_state.get("R") == 1

    res_false = Interpreter().run(prog, initial_state={"A": 10, "B": 5})
    assert res_false.final_state.get("R") == 0


def test_undefined_variable_raises_with_span() -> None:
    prog = parse("begin X := Y + 1 end", filename="undef.sipl")
    events: list[TraceEvent] = []
    interp = Interpreter(on_event=events.append)

    with pytest.raises(UndefinedVariableError) as exc_info:
        interp.run(prog)

    err = exc_info.value
    assert err.name == "Y"
    assert err.span is not None
    assert err.span.file == "undef.sipl"
    assert err.span.start_line == 1
    assert isinstance(events[-1], ExecutionErrorEvent)


def test_infinite_loop_hits_step_limit() -> None:
    prog = parse("begin while 1 = 1 do skip end", filename="loop.sipl")
    interp = Interpreter(max_steps=10)

    with pytest.raises(StepLimitExceededError) as exc_info:
        interp.run(prog)

    assert exc_info.value.max_steps == 10
    assert exc_info.value.step == 10


def test_trace_events_and_serialization() -> None:
    prog = parse("begin X := 1; if X > 0 then X := X + 2 else skip end", filename="tr.sipl")
    seen: list[TraceEvent] = []
    result = Interpreter(on_event=seen.append).run(prog)

    assert result.final_state.get("X") == 3
    assert result.trace == seen
    assert any(isinstance(e, BeforeStatementEvent) for e in result.trace)
    assert any(isinstance(e, ConditionEvaluatedEvent) and e.result for e in result.trace)
    assert any(
        isinstance(e, VariableChangedEvent) and e.name == "X" and e.old_value is None
        for e in result.trace
    )
    assert any(
        isinstance(e, VariableChangedEvent) and e.name == "X" and e.old_value == 1
        for e in result.trace
    )
    assert isinstance(result.trace[-1], ExecutionFinishedEvent)

    payload = result.to_dict()
    assert payload["final_state"] == {"X": 3}
    assert isinstance(payload["trace"], list)
    assert payload["trace"][-1]["event"] == "ExecutionFinished"


def test_state_overlay_and_helpers() -> None:
    s1 = State({"M": 8, "N": 16})
    s2 = s1.overlay({"M": 3, "X": 4})
    assert s1 == State({"M": 8, "N": 16})
    assert s2 == State({"M": 3, "N": 16, "X": 4})
    assert "X" in s2
    assert s2.copy() == s2