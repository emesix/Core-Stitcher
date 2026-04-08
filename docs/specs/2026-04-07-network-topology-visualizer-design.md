# VOS Network Topology Visualizer — Design Specification

**Date:** 2026-04-07
**Status:** Draft — pending external review (ChatGPT) before implementation
**Working name:** VOS-NetMap

## 1. Problem Statement

The VOS homelab network has 8+ managed devices across two 10G fabrics (frontend/backend), multiple VLANs, and Proxmox VMs/containers. During a single troubleshooting session on 2026-04-07, the following issues were caused by stale/missing documentation:

- Switch management IPs were wrong (.4/.5 → .30/.31, .6 → .32)
- Cable paths were unknown (HX310 nic1 → mystery device, not ONTi-BE as documented)
- SFP media converters were silently eating traffic (own MAC, no forwarding)
- VLAN membership had to be scraped from web UIs port-by-port
- No way to verify "does the physical network match the plan?"

Static markdown docs (`physical-wiring.md`) went stale within days of being written. ASCII diagrams in design specs don't update when cables move.

### 1.1 Core Insight

**MAC addresses don't lie.** If the plan says ONTi-BE port 7 should see MAC `84:8B:CD:4D:BD:30`, and it doesn't, something is wrong. The tool should make this comparison trivial and visual.

## 2. Goals

1. **Single source of truth** for the physical and logical network topology
2. **Layer-by-layer visualization** — physical devices → ports → cables → VLANs → IPs → services
3. **Planned vs actual verification** — define what SHOULD be, query what IS, highlight differences
4. **AI-maintained** — Claude generates and updates the topology by querying MCP tools (switchcraft, OPNsense, Proxmox)
5. **Human-reviewable** — JSON topology file lives in git, diffs are meaningful
6. **Portfolio-grade** — public GitHub audience, demonstrates network engineering competence

### 2.1 Non-Goals

- Not a monitoring/alerting system (Zabbix handles that)
- Not a configuration management tool (doesn't push changes to devices)
- Not a replacement for OPNsense/Proxmox UIs
- Not a general-purpose network diagram tool — purpose-built for VOS homelab

## 3. Architecture

### 3.1 Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | D3.js + vanilla JS/HTML | Full SVG control for VLAN wire overlays, zoom/pan, nested containers. React Flow can't do shifted parallel wires without heavy custom edge work |
| Backend | FastAPI (Python) | User's preferred stack, async, serves API + static frontend |
| Data store | JSON file on disk | Git-versionable, diffable, AI-readable/writable, no database overhead |
| Verification | MCP tools via gateway | switchcraft (MAC tables, VLANs, ports), OPNsense (interfaces, firewall), Proxmox (VMs, bridges, network config) |
| Deployment | Single container or bare Python | Lightweight, runs on any Proxmox LXC or Docker |

### 3.2 Component Diagram

```
┌─────────────────────────────────────────────┐
│                  Browser                     │
│  ┌───────────────────────────────────────┐  │
│  │         D3.js SVG Canvas              │  │
│  │  ┌─────────┐    ┌─────────┐          │  │
│  │  │ Device A │────│ Device B │          │  │
│  │  │ ┌─VM1─┐ │    │ ┌─VM2─┐ │          │  │
│  │  │ └─────┘ │    │ └─────┘ │          │  │
│  │  └─────────┘    └─────────┘          │  │
│  │     VLAN 25 ═══════╗                  │  │
│  │     VLAN 254 ──────╢                  │  │
│  │                    ║                  │  │
│  └───────────────────────────────────────┘  │
│  [Layer toggles] [Verify] [Export JSON]      │
└─────────────────────────────────────────────┘
              │ HTTP/JSON
┌─────────────────────────────────────────────┐
│           FastAPI Backend                    │
│  GET  /api/topology     → full topology     │
│  POST /api/verify       → run live checks   │
│  GET  /api/verify/last  → last result       │
│  POST /api/topology     → update topology   │
│  GET  /                 → serve frontend     │
└─────────────────────────────────────────────┘
              │ reads/writes
┌─────────────────────────────────────────────┐
│         topology.json (git-tracked)         │
└─────────────────────────────────────────────┘
              │ queries (during verify)
┌─────────────────────────────────────────────┐
│         MCP Gateway (localhost:4444)         │
│  switchcraft → MAC tables, VLANs, ports     │
│  OPNsense   → interfaces, firewall rules    │
│  Proxmox    → VMs, bridges, network config  │
└─────────────────────────────────────────────┘
```

## 4. Data Model

### 4.1 Topology JSON Structure

The topology is a single JSON file with four top-level sections:

```json
{
  "meta": {
    "version": "1.0",
    "name": "VOS Network",
    "updated": "2026-04-07T12:00:00Z",
    "updated_by": "claude"
  },
  "devices": { ... },
  "cables": [ ... ],
  "vlans": { ... }
}
```

### 4.2 Device Object

A device contains its interfaces (ports). VMs/containers/services are nested as child devices.

```json
{
  "devices": {
    "onti-be": {
      "name": "ONTi-BE",
      "type": "switch",
      "model": "S508CL-8S",
      "management_ip": "192.168.254.31",
      "position": { "x": 400, "y": 200 },
      "interfaces": {
        "eth1/0/1": {
          "type": "sfp+",
          "speed": "10G",
          "description": "Uplink to OPNsense ix1",
          "admin_status": "up",
          "vlans": {
            "mode": "trunk",
            "native_vlan": 1,
            "tagged": [25, 254]
          },
          "expected_neighbor": {
            "device": "opnsense",
            "interface": "ix1",
            "mac": "20:7C:14:F4:78:77"
          }
        },
        "eth1/0/7": {
          "type": "sfp+",
          "speed": "1G",
          "description": "HX310-DB backend NIC",
          "admin_status": "up",
          "vlans": {
            "mode": "trunk",
            "native_vlan": 1,
            "tagged": [25, 254]
          },
          "expected_neighbor": {
            "device": "pve-hx310-db",
            "interface": "nic1",
            "mac": "84:8B:CD:4D:BD:30"
          }
        }
      },
      "children": []
    },
    "pve-hx310-db": {
      "name": "pve-hx310-db",
      "type": "proxmox",
      "model": "HX310",
      "management_ip": "192.168.254.101",
      "position": { "x": 700, "y": 200 },
      "interfaces": {
        "nic0": {
          "type": "ethernet",
          "speed": "2.5G",
          "mac": "84:8B:CD:4D:B6:F0",
          "description": "Frontend via 91TSM",
          "bridge": "vmbr0",
          "vlans": {
            "mode": "access",
            "access_vlan": 254
          },
          "expected_neighbor": {
            "device": "91tsm",
            "interface": "port8",
            "mac": null
          }
        },
        "nic1": {
          "type": "ethernet",
          "speed": "1G",
          "mac": "84:8B:CD:4D:BD:30",
          "description": "Backend via ONTi-BE",
          "bridge": "vmbr1",
          "vlans": {
            "mode": "trunk",
            "tagged": [254],
            "bridge_vids": "254"
          },
          "expected_neighbor": {
            "device": "onti-be",
            "interface": "eth1/0/7"
          }
        }
      },
      "children": ["vm-100-lldap", "ct-101-docker"]
    }
  }
}
```

### 4.3 Cable Object

Cables connect two interfaces. They carry physical-layer info.

```json
{
  "cables": [
    {
      "id": "cable-be-hx310db",
      "type": "ethernet",
      "color": "purple-yellow",
      "endpoints": [
        { "device": "onti-be", "interface": "eth1/0/7" },
        { "device": "pve-hx310-db", "interface": "nic1" }
      ],
      "media": "1000BASE-T SFP + Cat6",
      "notes": "Requires 10Gtek 1000BASE-T SFP module in ONTi-BE slot"
    }
  ]
}
```

### 4.4 VLAN Object

VLANs are first-class entities with their own metadata.

```json
{
  "vlans": {
    "1": {
      "name": "default",
      "color": "#808080",
      "subnet": null
    },
    "25": {
      "name": "GeneralLAN",
      "color": "#4CAF50",
      "subnet": "192.168.25.0/24",
      "gateway": "192.168.25.1",
      "dhcp": true
    },
    "254": {
      "name": "Management",
      "color": "#2196F3",
      "subnet": "192.168.254.0/24",
      "gateway": "192.168.254.1",
      "dhcp": false
    }
  }
}
```

## 5. Visualization Design

### 5.1 Device Rendering

- Devices are **rounded rectangles** with an icon (switch, server, firewall, VM) and label
- **Ports** are rendered as small squares on the device border (left/right/top/bottom), labeled with interface name
- **Child devices** (VMs, containers, services) are rendered as smaller boxes **inside** the parent device box
- Devices are **draggable** — position saved to JSON

### 5.2 Cable Rendering

- Cables are **SVG paths** connecting port-to-port
- Persistent — always visible regardless of layer toggles
- Styled by cable type (ethernet = solid, DAC = dashed)
- Color matches physical cable color code (purple = backend, blue = frontend)

### 5.3 VLAN Overlay

- Each VLAN is a **parallel path** slightly offset from the cable path
- Color-coded by VLAN (green = VLAN 25, blue = VLAN 254)
- Toggle-able per VLAN from a legend/sidebar
- When a cable carries multiple VLANs, multiple shifted lines appear alongside it
- Native/untagged VLAN shown as solid line, tagged VLANs as dashed

### 5.4 Zoom & Navigation

- Mouse wheel zoom, click-drag pan (standard D3 zoom behavior)
- Click device → expand/highlight its ports and connections
- Click port → show detail panel (MAC, VLANs, expected neighbor, verification status)
- Click cable → show endpoints, VLANs carried, physical media info

### 5.5 Verification Status Indicators

- **Green dot** on port: live MAC matches expected MAC
- **Red dot** on port: live MAC doesn't match, or port is down when it should be up
- **Grey dot** on port: not yet verified
- **Orange dot** on port: port is up but no expected neighbor defined (unplanned connection)

## 6. Verification Engine

### 6.1 How Verification Works

When the user clicks "Verify" (or Claude triggers it via API):

1. For each device with a `management_ip`, query the appropriate MCP tool:
   - **Switches** (switchcraft): `get-vlans`, `get-ports`, MAC address table
   - **OPNsense**: `get-interfaces`, `get-firewall-rules`
   - **Proxmox**: `list-bridges`, `vm-info`, `node-status`

2. For each interface with an `expected_neighbor`:
   - Check if the expected MAC appears on that port
   - Check if the port is up/down
   - Check if VLAN membership matches the plan

3. Return a verification report:

```json
{
  "timestamp": "2026-04-07T12:00:00Z",
  "results": [
    {
      "device": "onti-be",
      "interface": "eth1/0/7",
      "status": "mismatch",
      "expected_mac": "84:8B:CD:4D:BD:30",
      "observed_mac": null,
      "expected_link": "up",
      "observed_link": "down",
      "message": "Port down — SFP module not installed"
    }
  ],
  "summary": { "ok": 12, "mismatch": 2, "unchecked": 3 }
}
```

### 6.2 MCP Integration

The verification engine calls MCP tools through the gateway at `localhost:4444`. It does NOT need its own MCP server initially — Claude can trigger verification via the FastAPI endpoint, or the web UI can call it directly.

Future: add an MCP server (borrowing homelable's pattern) so Claude can query the topology and verification results conversationally.

## 7. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve frontend (index.html + D3 app) |
| `GET` | `/api/topology` | Return full topology JSON |
| `POST` | `/api/topology` | Update topology JSON (full replace or merge) |
| `GET` | `/api/topology/export` | Download topology.json |
| `POST` | `/api/topology/import` | Upload topology.json |
| `POST` | `/api/verify` | Run live verification against MCP tools |
| `GET` | `/api/verify/last` | Return last verification result |
| `GET` | `/api/health` | Health check |

## 8. Project Structure

```
VOS-Network-Redux/
└── netmap/
    ├── backend/
    │   ├── main.py              # FastAPI app, serves frontend + API
    │   ├── verify.py            # Verification engine (queries MCP gateway)
    │   ├── models.py            # Pydantic models for topology JSON
    │   └── requirements.txt     # fastapi, uvicorn, httpx, pydantic
    ├── frontend/
    │   ├── index.html           # Single page app
    │   ├── js/
    │   │   ├── app.js           # Main D3 application
    │   │   ├── devices.js       # Device/port rendering
    │   │   ├── cables.js        # Cable + VLAN overlay rendering
    │   │   ├── verify.js        # Verification status overlay
    │   │   └── controls.js      # Zoom, pan, layer toggles, sidebar
    │   └── css/
    │       └── style.css        # Layout, device styles, VLAN colors
    ├── data/
    │   └── topology.json        # THE source of truth
    ├── Dockerfile
    ├── docker-compose.yml
    └── README.md
```

## 9. Implementation Phases

### Phase 1: Static Visualization (Session 1)
- Data model + topology.json with current VOS network
- D3 renderer: devices as boxes, ports on edges, cables as paths
- Zoom/pan/click
- No verification, no VLAN overlays yet

### Phase 2: VLAN Overlays + Detail Panels (Session 2)
- VLAN color-coded parallel paths on cables
- Layer toggles in sidebar
- Click-to-inspect panels for devices, ports, cables
- Child device rendering (VMs inside Proxmox hosts)

### Phase 3: Live Verification (Session 3)
- Verification engine querying MCP gateway
- Green/red/grey dots on ports
- Verification report panel
- "Verify" button in UI

### Phase 4: AI Integration (Session 4, optional)
- MCP server for Claude to read/modify topology
- Auto-generate topology.json from live MCP queries
- Claude-triggered verification from conversation

## 10. Borrowed From Homelable

Reference code at `/home/emesix/git/homelable/`:

| Component | Homelable source | What we borrow |
|-----------|-----------------|----------------|
| MCP server pattern | `mcp/app/tools.py` | Tool structure, SSE transport |
| Health checks | `backend/app/services/healthcheck.py` | Ping/TCP/HTTP check patterns |
| Device type icons | `frontend/src/components/canvas/nodes/` | Icon concepts, not actual React components |
| Docker Compose | `docker-compose.yml` | Service structure pattern |
| nmap scanner | `backend/app/services/scanner.py` | Discovery flow (Phase 4) |

## 11. Success Criteria

1. Opening the web page shows the VOS network with all devices, ports, cables, and VLANs
2. Clicking "Verify" checks live state against plan and shows green/red dots within 30 seconds
3. When a cable is moved or an SFP swapped, the mismatch is immediately visible after verification
4. The topology.json is human-readable and produces meaningful git diffs when updated
5. Claude can generate the initial topology.json from MCP queries without manual data entry

## 12. Open Questions

1. **Port positioning** — should ports auto-arrange on device borders, or be manually positioned?
2. **Firewall rules** — should the map show OPNsense firewall rules per VLAN, or keep that in OPNsense?
3. **Historical state** — should we keep verification history, or just latest state?
4. **Multi-site** — is this only for VOS, or should the data model support multiple sites?
