"""TUI application state — scope, selection, history, mode."""

from __future__ import annotations

from enum import StrEnum


class Mode(StrEnum):
    BROWSE = "browse"
    SELECT = "select"
    COMMAND = "command"
    WATCH = "watch"
    REVIEW = "review"
    FILTER = "filter"


class AppState:
    def __init__(self) -> None:
        self.mode: Mode = Mode.BROWSE
        self.scope: str | None = None
        self.selection: list[str] = []
        self.history: list[str] = []
        self.history_index: int = -1
        self.profile: str | None = None
        self.server: str | None = None
        self.connected: bool = False
        self.sidebar_visible: bool = True
        self.bottom_visible: bool = True

    @property
    def current_uri(self) -> str | None:
        if 0 <= self.history_index < len(self.history):
            return self.history[self.history_index]
        return None

    def navigate(self, uri: str) -> None:
        self.history = self.history[: self.history_index + 1]
        self.history.append(uri)
        self.history_index = len(self.history) - 1

    def go_back(self) -> None:
        if self.history_index > 0:
            self.history_index -= 1
        elif self.history_index == 0:
            self.history_index = -1

    def go_forward(self) -> None:
        if self.history_index < len(self.history) - 1:
            self.history_index += 1

    def toggle_selection(self, uri: str) -> None:
        if uri in self.selection:
            self.selection.remove(uri)
        else:
            self.selection.append(uri)

    def clear_selection(self) -> None:
        self.selection.clear()
