# Remote Debugging Setup

## tmux

Config at `~/.tmux.conf`. Prefix is `Ctrl+A` (not Ctrl+B — avoids conflicts with serial terminals).

### Key bindings

| Key | Action |
|---|---|
| `Ctrl+A \|` | Vertical split |
| `Ctrl+A -` | Horizontal split |
| `Ctrl+A c` | New window |
| `Ctrl+A h/j/k/l` | Navigate panes |
| `Ctrl+A S` | Serial: prompt for device, opens minicom 9600 |
| `Ctrl+A 4` | RS485: prompt for device, opens minicom 115200 |
| `Ctrl+A s` | SSH: prompt for target |
| `Ctrl+A O` | SSH to OPNsense (172.16.0.1) |
| `Ctrl+A G` | Tail MCP gateway logs |
| `Ctrl+A d` | Detach (session persists) |

### Typical lab session

```bash
tmux new -s lab
# Window 1: Claude Code
# Ctrl+A O  → Window 2: OPNsense SSH
# Ctrl+A S  → Window 3: Serial to switch (when USB adapter connected)
# Ctrl+A c  → Window 4: monitoring/logs
```

Reconnect after disconnect: `tmux a -t lab`

## Serial access

- **minicom**: full-featured, `minicom -D /dev/ttyUSB0 -b 9600`
- **picocom**: lightweight, `picocom /dev/ttyUSB0 -b 9600`
- Serial group: `uucp` on Arch Linux (not `dialout`)
- Common baud rates: 9600 (switches), 115200 (RS485/consoles)

## Lab devices

| Device | Access | Notes |
|---|---|---|
| OPNsense | SSH root@172.16.0.1 | Password auth enabled |
| ONTi switches | Serial + telnet (when powered) | admin/admin, old 192.168.254.x subnet |
| Zyxel GS1900 | SSH (when powered) | OpenWrt, root, no password |
