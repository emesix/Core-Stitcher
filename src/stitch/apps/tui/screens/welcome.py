"""Welcome screen — center workspace placeholder."""

from __future__ import annotations

from textual.widgets import Static

WELCOME_TEXT = """\
     _   _ _       _
 ___| |_(_) |_ ___| |__
/ __| __| | __/ __| '_ \\
\\__ \\ |_| | || (__| | | |
|___/\\__|_|\\__\\___|_| |_|

Welcome to Stitch TUI

Navigate devices in the sidebar, or press ^E to toggle it.
Use the bottom panel (^B) for logs, events, and steps.
"""


class WelcomeScreen(Static):
    """Center workspace showing a welcome message."""

    def __init__(self) -> None:
        super().__init__(WELCOME_TEXT, id="center")
