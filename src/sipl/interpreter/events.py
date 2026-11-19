"""Execution events and trace structures for SIPL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from sipl.ast import SourceSpan
from sipl.interpreter.state import State


@dataclass(frozen=True)
class BeforeStatementEvent:
    step: int
    stmt_type: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "BeforeStatement",
            "step": self.step,
            "stmt_type": self.stmt_type,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class AfterStatementEvent:
    step: int
    stmt_type: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "AfterStatement",
            "step": self.step,
            "stmt_type": self.stmt_type,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class VariableChangedEvent:
    step: int
    name: str
    old_value: int | None
    new_value: int
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "VariableChanged",
            "step": self.step,
            "name": self.name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class ConditionEvaluatedEvent:
    step: int
    result: bool
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "ConditionEvaluated",
            "step": self.step,
            "result": self.result,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True)
class ExecutionFinishedEvent:
    step: int
    final_state: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "ExecutionFinished",
            "step": self.step,
            "final_state": dict(self.final_state),
        }


@dataclass(frozen=True)
class ExecutionErrorEvent:
    step: int
    error_type: str
    message: str
    span: SourceSpan | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "ExecutionError",
            "step": self.step,
            "error_type": self.error_type,
            "message": self.message,
            "span": self.span.to_dict() if self.span is not None else None,
        }


TraceEvent: TypeAlias = (
    BeforeStatementEvent
    | AfterStatementEvent
    | VariableChangedEvent
    | ConditionEvaluatedEvent
    | ExecutionFinishedEvent
    | ExecutionErrorEvent
)


@dataclass(frozen=True)
class ExecutionResult:
    """Result of executing a SIPL program."""

    final_state: State
    steps: int
    trace: list[TraceEvent]

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_state": self.final_state.as_dict(),
            "steps": self.steps,
            "trace": [event.to_dict() for event in self.trace],
        }