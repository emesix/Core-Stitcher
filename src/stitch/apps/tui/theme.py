"""TUI CSS themes — dark, light, high-contrast."""

DARK_THEME = """\
Screen {
    background: #1a1a2e;
    color: #e0e0e0;
}

#top-bar {
    dock: top;
    height: 1;
    background: #12122a;
    color: #a0a0c0;
}

#sidebar {
    width: 32;
    background: #16162e;
    border-right: solid #2a2a4e;
}

#center {
    background: #1a1a2e;
}

#bottom-panel {
    height: 10;
    background: #12122a;
    border-top: solid #2a2a4e;
}

#footer {
    dock: bottom;
    height: 1;
    background: #12122a;
    color: #606080;
}

.status-ok {
    color: #00e676;
}

.status-warning {
    color: #ffab40;
}

.status-error {
    color: #ff5252;
}

.status-running {
    color: #40c4ff;
}

.status-pending {
    color: #ffd740;
}

.status-cancelled {
    color: #9e9e9e;
}

.focused {
    border: tall #7c4dff;
}

.label {
    color: #b0b0d0;
    text-style: bold;
}
"""

LIGHT_THEME = """\
Screen {
    background: #fafafa;
    color: #212121;
}

#top-bar {
    dock: top;
    height: 1;
    background: #e0e0e0;
    color: #424242;
}

#sidebar {
    width: 32;
    background: #f5f5f5;
    border-right: solid #bdbdbd;
}

#center {
    background: #fafafa;
}

#bottom-panel {
    height: 10;
    background: #e0e0e0;
    border-top: solid #bdbdbd;
}

#footer {
    dock: bottom;
    height: 1;
    background: #e0e0e0;
    color: #757575;
}

.status-ok {
    color: #2e7d32;
}

.status-warning {
    color: #f57f17;
}

.status-error {
    color: #c62828;
}

.status-running {
    color: #0277bd;
}

.status-pending {
    color: #f9a825;
}

.status-cancelled {
    color: #757575;
}

.focused {
    border: tall #651fff;
}

.label {
    color: #424242;
    text-style: bold;
}
"""

HIGH_CONTRAST_THEME = """\
Screen {
    background: #000000;
    color: #ffffff;
}

#top-bar {
    dock: top;
    height: 1;
    background: #000000;
    color: #ffffff;
    border-bottom: solid #ffffff;
}

#sidebar {
    width: 32;
    background: #000000;
    border-right: solid #ffffff;
}

#center {
    background: #000000;
}

#bottom-panel {
    height: 10;
    background: #000000;
    border-top: solid #ffffff;
}

#footer {
    dock: bottom;
    height: 1;
    background: #000000;
    color: #ffffff;
    border-top: solid #ffffff;
}

.status-ok {
    color: #00ff00;
}

.status-warning {
    color: #ffff00;
}

.status-error {
    color: #ff0000;
}

.status-running {
    color: #00ffff;
}

.status-pending {
    color: #ffff00;
}

.status-cancelled {
    color: #808080;
}

.focused {
    border: tall #ffffff;
}

.label {
    color: #ffffff;
    text-style: bold;
}
"""

THEMES: dict[str, str] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "high-contrast": HIGH_CONTRAST_THEME,
}
