"""Interpreter engine for SIPL with step limiting and event tracing."""

from __future__ import annotations

from collections.abc import Callable, Mapping

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
from sipl.errors import SiplRuntimeError, StepLimitExceededError
from sipl.interpreter.events import (
    AfterStatementEvent,
    BeforeStatementEvent,
    ConditionEvaluatedEvent,
    ExecutionErrorEvent,
    ExecutionFinishedEvent,
    ExecutionResult,
    TraceEvent,
    VariableChangedEvent,
)
from sipl.interpreter.state import State

EventCallback = Callable[[TraceEvent], None]


class Interpreter:
    """Executes SIPL Program ASTs on an initial variable state."""

    def __init__(
        self,
        max_steps: int = 10_000,
        collect_trace: bool = True,
        on_event: EventCallback | None = None,
    ) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self.max_steps = max_steps
        self.collect_trace = collect_trace
        self.on_event = on_event
        self._steps = 0
        self._trace: list[TraceEvent] = []

    def run(
        self,
        program: Program,
        initial_state: Mapping[str, int] | None = None,
    ) -> ExecutionResult:
        """Execute a SIPL program and return its final state, step count, and trace."""
        self._steps = 0
        self._trace = []
        state = State(initial_state)

        try:
            self._exec_stmt(program.body, state)
        except SiplRuntimeError as exc:
            if exc.step is None:
                exc.step = self._steps
            self._emit(
                ExecutionErrorEvent(
                    step=self._steps,
                    error_type=type(exc).__name__,
                    message=exc.message,
                    span=exc.span,
                )
            )
            raise

        self._emit(
            ExecutionFinishedEvent(
                step=self._steps,
                final_state=state.as_dict(),
            )
        )
        return ExecutionResult(
            final_state=state,
            steps=self._steps,
            trace=list(self._trace),
        )

    def _emit(self, event: TraceEvent) -> None:
        if self.collect_trace:
            self._trace.append(event)
        if self.on_event is not None:
            self.on_event(event)

    def _tick_step(self, span: SourceSpan) -> int:
        if self._steps >= self.max_steps:
            raise StepLimitExceededError(
                max_steps=self.max_steps,
                span=span,
                step=self._steps,
            )
        self._steps += 1
        return self._steps

    def _exec_stmt(self, stmt: Stmt, state: State) -> None:
        if isinstance(stmt, SeqStmt):
            self._exec_stmt(stmt.first, state)
            self._exec_stmt(stmt.second, state)
            return

        stmt_type = type(stmt).__name__
        if isinstance(stmt, AssignStmt):
            step = self._tick_step(stmt.span)
            self._emit(BeforeStatementEvent(step=step, stmt_type=stmt_type, span=stmt.span))
            new_val = self.eval_aexp(stmt.value, state)
            old_val = state.get_optional(stmt.target)
            state.set(stmt.target, new_val)
            self._emit(
                VariableChangedEvent(
                    step=step,
                    name=stmt.target,
                    old_value=old_val,
                    new_value=new_val,
                    span=stmt.span,
                )
            )
            self._emit(AfterStatementEvent(step=step, stmt_type=stmt_type, span=stmt.span))
        elif isinstance(stmt, SkipStmt):
            step = self._tick_step(stmt.span)
            self._emit(BeforeStatementEvent(step=step, stmt_type=stmt_type, span=stmt.span))
            self._emit(AfterStatementEvent(step=step, stmt_type=stmt_type, span=stmt.span))
        elif isinstance(stmt, BlockStmt):
            step = self._tick_step(stmt.span)
            self._emit(BeforeStatementEvent(step=step, stmt_type=stmt_type, span=stmt.span))
            self._exec_stmt(stmt.body, state)
            self._emit(AfterStatementEvent(step=self._steps, stmt_type=stmt_type, span=stmt.span))
        elif isinstance(stmt, IfStmt):
            step = self._tick_step(stmt.span)
            self._emit(BeforeStatementEvent(step=step, stmt_type=stmt_type, span=stmt.span))
            cond = self.eval_bexp(stmt.condition, state)
            self._emit(
                ConditionEvaluatedEvent(step=step, result=cond, span=stmt.condition.span)
            )
            if cond:
                self._exec_stmt(stmt.then_branch, state)
            else:
                self._exec_stmt(stmt.else_branch, state)
            self._emit(AfterStatementEvent(step=self._steps, stmt_type=stmt_type, span=stmt.span))
        elif isinstance(stmt, WhileStmt):
            entry_step = self._steps
            self._emit(
                BeforeStatementEvent(step=entry_step, stmt_type=stmt_type, span=stmt.span)
            )
            while True:
                iter_step = self._tick_step(stmt.span)
                cond = self.eval_bexp(stmt.condition, state)
                self._emit(
                    ConditionEvaluatedEvent(
                        step=iter_step,
                        result=cond,
                        span=stmt.condition.span,
                    )
                )
                if not cond:
                    break
                self._exec_stmt(stmt.body, state)
            self._emit(AfterStatementEvent(step=self._steps, stmt_type=stmt_type, span=stmt.span))
        else:
            raise TypeError(f"Unsupported statement node: {type(stmt).__name__}")

    def eval_aexp(self, expr: AExp, state: State) -> int:
        """Evaluate an arithmetic expression in the given state."""
        if isinstance(expr, IntLiteral):
            return expr.value
        if isinstance(expr, VarExpr):
            return state.get(expr.name, span=expr.span)
        if isinstance(expr, BinaryArithExpr):
            left = self.eval_aexp(expr.left, state)
            right = self.eval_aexp(expr.right, state)
            if expr.op == "+":
                return left + right
            if expr.op == "-":
                return left - right
            if expr.op == "*":
                return left * right
            raise ValueError(f"Unsupported arithmetic operator: {expr.op}")
        raise TypeError(f"Unsupported AExp node: {type(expr).__name__}")

    def eval_bexp(self, expr: BExp, state: State) -> bool:
        """Evaluate a boolean expression in the given state."""
        if isinstance(expr, CompareExpr):
            left = self.eval_aexp(expr.left, state)
            right = self.eval_aexp(expr.right, state)
            if expr.op == "=":
                return left == right
            if expr.op == ">":
                return left > right
            raise ValueError(f"Unsupported comparison operator: {expr.op}")
        if isinstance(expr, NotExpr):
            return not self.eval_bexp(expr.operand, state)
        if isinstance(expr, OrExpr):
            return self.eval_bexp(expr.left, state) or self.eval_bexp(expr.right, state)
        raise TypeError(f"Unsupported BExp node: {type(expr).__name__}")