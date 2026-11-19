"""Variable state representation for SIPL."""

from __future__ import annotations

from collections.abc import Mapping

from sipl.ast import SourceSpan
from sipl.errors import UndefinedVariableError


class State:
    """Mutable mapping from variable names to integer values (Var -> Int)."""

    def __init__(self, initial: Mapping[str, int] | None = None) -> None:
        self._values: dict[str, int] = dict(initial) if initial is not None else {}

    def get(self, name: str, span: SourceSpan | None = None) -> int:
        """Dereference variable (x=>). Raises UndefinedVariableError if absent."""
        if name not in self._values:
            raise UndefinedVariableError(name=name, span=span)
        return self._values[name]

    def get_optional(self, name: str) -> int | None:
        return self._values.get(name)

    def set(self, name: str, value: int) -> None:
        self._values[name] = value

    def overlay(self, other: Mapping[str, int]) -> State:
        """Return a new State combining self with other (st ∇ other)."""
        merged = dict(self._values)
        merged.update(other)
        return State(merged)

    def copy(self) -> State:
        return State(self._values)

    def as_dict(self) -> dict[str, int]:
        return dict(self._values)

    def __contains__(self, name: str) -> bool:
        return name in self._values

    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self._values == other._values
        return NotImplemented

    def __repr__(self) -> str:
        items = ", ".join(f"{k} -> {v}" for k, v in self._values.items())
        return f"State([{items}])"