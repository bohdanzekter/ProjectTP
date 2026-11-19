"""Error types with SourceSpan diagnostics for SIPL."""

from __future__ import annotations

from typing import Any

from sipl.ast import SourceSpan


class SiplError(Exception):
    """Base error for all SIPL frontend and runtime errors."""

    def __init__(self, message: str, span: SourceSpan | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": type(self).__name__,
            "message": self.message,
            "span": self.span.to_dict() if self.span is not None else None,
        }


class SiplSyntaxError(SiplError):
    """Syntax or lexical error raised during SIPL parsing."""

    def __init__(
        self,
        message: str,
        span: SourceSpan,
        snippet: str = "",
    ) -> None:
        super().__init__(message, span)
        self.snippet = snippet

    def __str__(self) -> str:
        if self.span is None:
            return self.message
        loc = f"{self.span.file}:{self.span.start_line}:{self.span.start_col}"
        if self.snippet:
            return f"{loc}: {self.message}\n{self.snippet}"
        return f"{loc}: {self.message}"