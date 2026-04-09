"""Shared error types across commands, queries, and streams."""

from __future__ import annotations

from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class StitchError(BaseModel):
    """Domain/protocol error returned by the server."""

    code: str
    message: str
    retryable: bool
    detail: dict | None = None
    correlation_id: str | None = None
    field_errors: list[FieldError] | None = None


class TransportError(BaseModel):
    """Transport-level failure (timeout, broken connection, gateway error)."""

    kind: str
    message: str
    retryable: bool
    detail: dict | None = None


class StitchAPIError(Exception):
    """Raiseable wrapper around StitchError."""

    def __init__(self, error: StitchError) -> None:
        self.error = error
        super().__init__(error.message)

    @property
    def code(self) -> str:
        return self.error.code

    @property
    def retryable(self) -> bool:
        return self.error.retryable


class StitchTransportError(Exception):
    """Raiseable wrapper around TransportError."""

    def __init__(self, error: TransportError) -> None:
        self.error = error
        super().__init__(error.message)

    @property
    def kind(self) -> str:
        return self.error.kind

    @property
    def retryable(self) -> bool:
        return self.error.retryable
