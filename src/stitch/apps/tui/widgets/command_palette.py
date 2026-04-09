"""Command palette overlay — Ctrl+P."""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList


class CommandPalette(ModalScreen):
    """Modal command palette for quick actions."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
    }
    #palette-container {
        width: 60;
        max-height: 20;
        background: #2d2d44;
        border: solid #7ec8e3;
        padding: 1;
    }
    #palette-input {
        margin-bottom: 1;
    }
    """

    DEFAULT_COMMANDS: list[tuple[str, str]] = [
        ("device list", "Show device list"),
        ("preflight run", "Run preflight verification"),
        ("trace run", "Trace VLAN path"),
        ("run list", "Show run list"),
        ("system health", "System health check"),
    ]

    def __init__(self, commands: list[tuple[str, str]] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._commands = commands or self.DEFAULT_COMMANDS

    def compose(self):
        with Vertical(id="palette-container"):
            yield Input(placeholder="Type a command...", id="palette-input")
            yield OptionList(
                *[f"{cmd} — {desc}" for cmd, desc in self._commands],
                id="palette-options",
            )

    def on_mount(self) -> None:
        self.query_one("#palette-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        options = self.query_one("#palette-options", OptionList)
        options.clear_options()
        for cmd, desc in self._commands:
            if query in cmd.lower() or query in desc.lower():
                options.add_option(f"{cmd} — {desc}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.prompt))
