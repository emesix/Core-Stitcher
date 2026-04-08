# VOS-Preflight — Final Design Specification

**Date:** 2026-04-07
**Status:** Final — ready for implementation
**Working name:** VOS-Preflight
**Revision:** 3 — cables→links unification (internal + external as same graph edge type)

---

## 1. One-Sentence Summary

VOS-Preflight is a port-and-link truth model with live verification that catches mismatches between planned and actual network state, answering "where is it broken?" and "what breaks if I change this?"

---

## 2. Problem

On 2026-04-07, a single troubleshooting session wasted hours because:

- Switch IPs were wrong in config files (.4/.5 vs .30/.31)
- Cable paths were unknown (HX310 nic1 → mystery device)
- SFP media converters silently ate traffic (own MAC, no forwarding)
- VLAN membership had to be scraped from web UIs port by port
- No way to verify "does the physical network match the plan?"

Root cause: no machine-readable model of what ports connect to what, carrying which VLANs, expecting which MACs.

---

## 3. Design Philosophy

### 3.1 Minimal stored model, richer derived queries

The persisted model contains only what is physically or logically declared: devices, ports, links, VLANs, expected neighbors. No path objects. No dependency chains. No constraint language.

Diagnostic views — VLAN traces, impact previews, verification reports — are **computed at query time** from the graph, not stored as first-class entities. This keeps the model simple, diffable, and hard to get out of sync.

### 3.2 MAC addresses don't lie

The strongest local truth is the MAC address. Human labels drift. Port names change between vendors. But if ONTi-BE port 7 should see MAC `84:8B:CD:4D:BD:30` and doesn't, something is wrong. MAC-based expected neighbors are the core of verification.

### 3.3 Faults are on ports and links, not on paths

A "broken VLAN 254 path" is really a broken port or a broken link. The model stores the truth at that granularity. The engine derives which VLAN chains are affected.

### 3.4 AI must inspect before acting

The AI workflow is procedural, not inferential:

1. Query model
2. Run verification
3. Run VLAN trace
4. Run change preview
5. Propose fix
6. Execute only with human approval
7. Re-verify

This does not require stored dependency or constraint objects. It requires the API contract to force those calls.

### 3.5 Model authority

`topology.json` is the reviewed working truth for V1. Not the forever-architecture. It may later be ingested from NetBox or generated from live discovery. For now it is hand-maintained and git-tracked.

---

## 4. Stored Model

Three entities. VLANs are properties of ports, not separate operational objects. A VLAN registry provides metadata only.

| Entity | What it represents |
|--------|-------------------|
| **Device** | A physical or virtual thing that has ports |
| **Port** | An interface on a device — physical, bridge, VLAN subinterface, or virtual NIC |
| **Link** | A connection between two ports — physical cable OR internal logical hop |

Ports are the **vertices**. Links are the **edges**. Some links are physical (cables), some are internal (bridge membership, VLAN parent). The graph traversal engine treats them identically. The verification checks differ by link type.

### 4.1 Complete JSON Structure

```json
{
  "meta": {
    "version": "1.0",
    "name": "VOS Network",
    "updated": "2026-04-07T12:00:00Z",
    "updated_by": "claude"
  },
  "vlans": {},
  "devices": {},
  "links": []
}
```

### 4.2 VLAN Registry

Metadata only. The operational truth is on the ports.

```json
{
  "vlans": {
    "1":   { "name": "default",    "color": "#808080", "subnet": null,                "gateway": null },
    "25":  { "name": "GeneralLAN", "color": "#4CAF50", "subnet": "192.168.25.0/24",   "gateway": "192.168.25.1" },
    "254": { "name": "Management", "color": "#2196F3", "subnet": "192.168.254.0/24",  "gateway": "192.168.254.1" }
  }
}
```

### 4.3 Device

A device has metadata and ports. Child devices (VMs, containers) are listed by ID.

```json
{
  "onti-be": {
    "name": "ONTi-BE",
    "type": "switch",
    "model": "S508CL-8S",
    "management_ip": "192.168.254.31",
    "mcp_source": "switchcraft:onti-backend",
    "position": { "x": 400, "y": 200 },
    "ports": {
      "eth1": {
        "device_name": "Ethernet1/0/1",
        "type": "sfp+",
        "speed": "10G",
        "mac": null,
        "description": "Uplink to OPNsense ix1",
        "vlans": { "mode": "trunk", "native": 1, "tagged": [25, 254] },
        "expected_neighbor": {
          "device": "opnsense",
          "port": "ix1",
          "mac": "20:7C:14:F4:78:77"
        }
      },
      "eth7": {
        "device_name": "Ethernet1/0/7",
        "type": "sfp+",
        "speed": "1G",
        "mac": null,
        "description": "HX310-DB backend NIC",
        "vlans": { "mode": "trunk", "native": 1, "tagged": [25, 254] },
        "expected_neighbor": {
          "device": "pve-hx310-db",
          "port": "nic1",
          "mac": "84:8B:CD:4D:BD:30"
        }
      }
    },
    "children": []
  }
}
```

### 4.4 Port Types

All are modeled the same way. The `type` field distinguishes them:

| Type | Examples | Notes |
|------|----------|-------|
| `sfp+` | Switch SFP+ ports | Physical, may need SFP module |
| `ethernet` | RJ45 NICs | Physical copper |
| `bridge` | vmbr0, vmbr1, bridge0 | Logical. `bridge_ports` lists member physical ports |
| `vlan` | vlan01, vlan02 | Logical. `parent_port` references the trunk port |
| `virtual` | vtnet0 | VM/hypervisor internal NIC |

Bridge and VLAN subinterface ports participate in graph traversal exactly like physical ports. They are intra-device hops.

### 4.5 Links

Every connection between two ports — physical or logical.

**Link types:**

| Type | What it represents | Verification checks |
|------|-------------------|-------------------|
| `physical_cable` | External cable between devices | Link up/down, neighbor MAC present, VLAN compatibility |
| `bridge_member` | Port is member of a bridge | Bridge membership exists, bridge_vlan_aware correct, bridge_vids contains expected VLANs |
| `vlan_parent` | VLAN subinterface on a trunk port | Parent port up, VLAN ID present on parent |
| `internal_virtual` | VM NIC to hypervisor bridge, switch backplane | Interface present and up |

**Example — full link set for one path (OPNsense → ONTi-BE → HX310-db):**

```json
{
  "links": [
    {
      "id": "phys-opnsense-ix1-to-onti-be-eth1",
      "type": "physical_cable",
      "endpoints": [
        { "device": "opnsense", "port": "ix1" },
        { "device": "onti-be", "port": "eth1" }
      ],
      "media": "DAC SFP+ 0.5m",
      "cable_color": "black"
    },
    {
      "id": "phys-onti-be-eth7-to-hx310db-nic1",
      "type": "physical_cable",
      "endpoints": [
        { "device": "onti-be", "port": "eth7" },
        { "device": "pve-hx310-db", "port": "nic1" }
      ],
      "media": "10Gtek 1000BASE-T SFP + Cat6",
      "cable_color": "purple-yellow",
      "notes": "Awaiting 10Gtek SFP modules (ordered 2026-04-07)"
    },
    {
      "id": "bridge-hx310db-nic1-to-vmbr1",
      "type": "bridge_member",
      "endpoints": [
        { "device": "pve-hx310-db", "port": "nic1" },
        { "device": "pve-hx310-db", "port": "vmbr1" }
      ]
    },
    {
      "id": "vlan-opnsense-ix1-to-vlan03",
      "type": "vlan_parent",
      "endpoints": [
        { "device": "opnsense", "port": "ix1" },
        { "device": "opnsense", "port": "vlan03" }
      ]
    },
    {
      "id": "bridge-opnsense-vlan03-to-bridge0",
      "type": "bridge_member",
      "endpoints": [
        { "device": "opnsense", "port": "vlan03" },
        { "device": "opnsense", "port": "bridge0" }
      ]
    },
    {
      "id": "bridge-opnsense-vtnet0-to-bridge0",
      "type": "bridge_member",
      "endpoints": [
        { "device": "opnsense", "port": "vtnet0" },
        { "device": "opnsense", "port": "bridge0" }
      ]
    }
  ]
}
```

This makes the graph complete: a VLAN 254 trace from OPNsense to HX310-db walks bridge0 → vlan03 → ix1 → [cable] → onti-be:eth1 → onti-be:eth7 → [cable] → nic1 → vmbr1. Every hop is a link. Every link is verifiable.

---

## 5. Derived Diagnostic Views

These are NOT stored. They are computed from the graph + live state at query time.

### 5.1 Verification View

Per-port and per-link comparison of declared vs observed state.

**What it checks per link (varies by link type):**

| Check | Applies to | How | Flag condition |
|-------|-----------|-----|----------------|
| Link status | `physical_cable` | Query device for port up/down | Down when link exists |
| Neighbor MAC | `physical_cable` | Query switch MAC table | Expected MAC absent |
| Unexpected MAC | `physical_cable` | Query switch MAC table | Unknown MAC present on port |
| VLAN compatibility | `physical_cable`, `bridge_member` | Compare both endpoints | Incompatible VLAN config (see 5.4) |
| Bridge membership | `bridge_member` | Query bridge config | Port not member of bridge |
| Bridge VLAN config | `bridge_member` | Query bridge_vids | Expected VLAN not in bridge_vids |
| VLAN parent exists | `vlan_parent` | Query parent port | Parent port down or VLAN not configured |
| Interface present | `internal_virtual` | Query device | Interface missing or down |
| Management reachable | all (device-level) | Ping management_ip | Device unreachable |

**Observation confidence:**

Each live observation carries a `source` field:

| Source | Meaning | Trust level |
|--------|---------|-------------|
| `mcp_live` | Queried from MCP tool just now | Highest |
| `declared` | From topology.json | High (human-reviewed) |
| `inferred` | Derived from other observations | Medium |
| `unknown` | No data available | Lowest |

The verifier trusts `mcp_live` over `declared` when they conflict.

**Output format:**

```json
{
  "timestamp": "2026-04-07T14:30:00Z",
  "results": [
    {
      "link": "phys-onti-be-eth7-to-hx310db-nic1",
      "link_type": "physical_cable",
      "status": "fail",
      "checks": [
        {
          "check": "link_status",
          "port": "onti-be:eth7",
          "expected": "up",
          "observed": "down",
          "source": "mcp_live",
          "flag": "error"
        },
        {
          "check": "unexpected_mac",
          "port": "onti-be:eth8",
          "expected_mac": "84:8B:CD:4D:BC:8F",
          "observed_mac": "EC:43:F6:FF:2D:8D",
          "source": "mcp_live",
          "flag": "error",
          "message": "Unexpected MAC — media converter instead of HX310"
        }
      ]
    }
  ],
  "summary": { "total_links": 12, "ok": 10, "warn": 1, "fail": 1 }
}
```

### 5.2 VLAN Trace View

Ordered traversal of a VLAN from source to target, with mismatch overlay.

**Input:** VLAN ID + optional source device + optional target device.

**Algorithm:**

1. Build subgraph: all ports and links where the port carries the specified VLAN (tagged or access)
2. If source and target given: find ordered path through the subgraph using BFS/DFS
3. If only VLAN given: return all connected components carrying that VLAN
4. Overlay live verification state on each hop
5. Report first failed hop as the break point

**Output:**

```json
{
  "vlan": 254,
  "source": "opnsense",
  "target": "pve-hx310-db",
  "status": "broken",
  "hops": [
    { "device": "opnsense",     "port": "bridge0",  "status": "ok",   "source": "mcp_live" },
    { "device": "opnsense",     "port": "vlan03",   "status": "ok",   "source": "mcp_live" },
    { "device": "opnsense",     "port": "ix1",      "status": "ok",   "source": "mcp_live" },
    { "link": "phys-opnsense-ix1-to-onti-be-eth1",   "status": "ok",   "source": "mcp_live" },
    { "device": "onti-be",      "port": "eth1",     "status": "ok",   "source": "mcp_live" },
    { "device": "onti-be",      "port": "eth7",     "status": "fail", "source": "mcp_live",
      "reason": "link down, expected MAC absent" },
    { "link": "phys-onti-be-eth7-to-hx310db-nic1",   "status": "fail", "source": "declared" },
    { "device": "pve-hx310-db", "port": "nic1",     "status": "unknown", "source": "unknown" }
  ],
  "first_break": {
    "device": "onti-be",
    "port": "eth7",
    "reason": "link down, expected MAC absent",
    "likely_causes": ["missing or failed SFP module", "bad cable", "port disabled"]
  }
}
```

### 5.3 Change Impact View

Computed affected subgraph for a proposed modification.

**Input:** A proposed change (add/remove VLAN, disable port, change trunk mode).

**Algorithm:**

1. Find the target port
2. Find all links connected to that port
3. Find all ports on the other end of those links
4. For each affected port, check: does this change break VLAN compatibility?
5. For each affected VLAN, find all other ports/links carrying it — those are indirectly affected
6. Return the affected set with risk assessment

**Output:**

```json
{
  "proposed_change": {
    "action": "remove_vlan",
    "device": "onti-be",
    "port": "eth7",
    "vlan": 254
  },
  "impact": [
    {
      "device": "pve-hx310-db",
      "port": "nic1",
      "effect": "loses VLAN 254 on backend path",
      "severity": "high"
    }
  ],
  "risk": "high",
  "safe_to_apply": false
}
```

### 5.4 VLAN Compatibility Rules

Not "same config on both ends" but "compatible relationship":

| Port A | Port B | Compatible? |
|--------|--------|-------------|
| Trunk tagged [25,254] | Trunk tagged [254] | **Yes** — B subscribes to subset |
| Trunk tagged [25,254] | Access VLAN 254 | **Yes** — switch terminates trunk, host receives untagged |
| Access VLAN 25 | Access VLAN 254 | **No** — different VLANs on same link |
| Trunk tagged [25] | Trunk tagged [254] | **Flag** — no shared VLANs, link carries nothing useful |
| Trunk tagged [25,254] | Trunk tagged [25,254] | **Yes** — symmetric |

The check flags **incompatible** configs (mismatched access VLANs, no shared VLANs on a trunk). Asymmetric subsets are informational, not errors.

---

## 6. Architecture

### 6.1 Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python) |
| Data store | `topology.json` on disk (git-tracked) |
| Live queries | httpx → MCP Gateway (localhost:4444) + direct telnet/SSH |
| Frontend | D3.js + vanilla HTML/CSS/JS |
| Deployment | Bare Python or single Docker container |

### 6.2 System Diagram

```
Browser (D3.js)
    │
    │ GET  /api/topology
    │ POST /api/verify
    │ POST /api/trace-vlan
    │ POST /api/preview-change
    │
FastAPI Backend
    │
    ├── reads/writes → topology.json (git repo)
    │
    └── queries (during verify) → MCP Gateway :4444
                                    ├── switchcraft
                                    ├── opnsense
                                    └── proxmox
```

---

## 7. MCP Adapters

Each device type maps to an MCP source for live queries:

| Device type | MCP tool | What we query |
|-------------|----------|--------------|
| switch (onti-ogf) | switchcraft + telnet `show mac-address-table`, `show vlan`, `show interface` | Port status, VLAN membership, MAC table |
| switch (jtcom) | switchcraft + HTTP `/mac.cgi`, `/vlan.cgi?page=port_based` | Port status, VLAN membership, MAC table |
| firewall (opnsense) | opnsense `get-interfaces` | Interface status, IPs, VLAN config |
| proxmox | proxmox `list-bridges`, `node-status` | Bridge config, bridge_vids, NIC status |

Specific API patterns (from ChatGPT research):

- **Proxmox:** `GET /nodes/{node}/network` returns interfaces with type, active, addresses
- **OPNsense:** `GET /api/interfaces/overview/interfacesInfo` returns all interface states
- **Switches:** MCP switchcraft tools + raw telnet/HTTP for MAC tables not exposed via MCP

---

## 8. API Endpoints

### 8.1 Topology

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/topology` | Return full topology JSON |
| `POST` | `/api/topology` | Replace full topology JSON |
| `GET` | `/api/topology/export` | Download topology.json |
| `POST` | `/api/topology/import` | Upload topology.json |

### 8.2 Verification

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/api/verify` | `{}` or `{"device": "onti-be"}` | Full or single-device verification |
| `GET` | `/api/verify/last` | — | Last verification result |

### 8.3 Diagnostics

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/api/trace-vlan` | `{"vlan": 254, "source": "opnsense", "target": "pve-hx310-db"}` | Ordered VLAN trace |
| `POST` | `/api/preview-change` | `{"action": "remove_vlan", "device": "onti-be", "port": "eth7", "vlan": 254}` | Change impact preview |

### 8.4 System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve frontend |
| `GET` | `/api/health` | Health check |

---

## 9. Frontend Visualization

### 9.1 Devices
- Rounded rectangles with icon and label
- Ports as small labeled squares on border
- Child devices as smaller boxes inside parent
- Draggable — position saved to topology.json

### 9.2 Cables
- SVG paths connecting port-to-port
- Always visible regardless of layer toggles
- Physical links: color from cable_color field. Logical links: rendered as short internal connectors within device box

### 9.3 VLAN Overlay
- Parallel lines offset from link path, one per VLAN
- Color from VLAN registry
- Toggle per VLAN from sidebar legend
- Access/native = solid, tagged = dashed

### 9.4 Verification Overlay
- Green dot: all checks pass
- Red dot: any check failed
- Orange dot: warning (unexpected MAC, informational asymmetry)
- Grey dot: not yet verified
- Click port → detail panel with check results

### 9.5 Interaction
- Mouse wheel zoom, click-drag pan
- Click device → highlight connections
- Click link → show VLANs carried, verification status, link type
- Click port → MAC, VLANs, expected neighbor, observed state
- Sidebar: VLAN toggles, Verify button, last verification summary

---

## 10. Project Structure

```
VOS-Network-Redux/
└── preflight/
    ├── backend/
    │   ├── main.py              # FastAPI app
    │   ├── verify.py            # Verification engine
    │   ├── trace.py             # VLAN trace (graph traversal)
    │   ├── impact.py            # Change impact preview
    │   ├── adapters/
    │   │   ├── switchcraft.py   # Switch MCP adapter
    │   │   ├── opnsense.py      # OPNsense MCP adapter
    │   │   └── proxmox.py       # Proxmox MCP adapter
    │   ├── models.py            # Pydantic models for topology
    │   └── requirements.txt
    ├── frontend/
    │   ├── index.html
    │   ├── js/
    │   │   ├── app.js           # D3 main application
    │   │   ├── devices.js       # Device + port rendering
    │   │   ├── links.js          # Link + VLAN overlay rendering
    │   │   ├── verify.js        # Verification status overlay
    │   │   └── controls.js      # Zoom, pan, legend, sidebar
    │   └── css/
    │       └── style.css
    ├── data/
    │   └── topology.json
    ├── Dockerfile
    └── README.md
```

---

## 11. Implementation Phases

### Phase 1 — Model + Verification Engine (Session 1)

- Pydantic models for topology.json
- Full topology.json populated with current VOS network
- Verification engine with MCP adapters
- VLAN trace engine (graph traversal)
- Change impact engine
- FastAPI serving all endpoints
- CLI test: run verify, trace, preview — get JSON reports

**Success:** `POST /api/verify` returns green/red per link with real data. `POST /api/trace-vlan` finds the first broken hop including internal hops.

### Phase 2 — Web UI (Session 2)

- D3.js canvas: devices, ports, links (physical + internal)
- VLAN overlay rendering
- Verification dot overlay
- Zoom/pan/click interactions
- Sidebar with VLAN toggles and verify button

**Success:** Open browser, see network, click Verify, see green/red dots, click port to see details.

### Phase 3 — AI Integration (Session 3, optional)

- MCP server exposing topology/verify/trace/preview tools
- Claude queries preflight before proposing infra changes
- Post-change verification workflow

**Success:** Claude no longer proposes ad hoc infra changes without model-backed checks.

---

## 12. Reference Code

From homelable (`/home/emesix/git/homelable/`):

| Component | Source | What we borrow |
|-----------|--------|---------------|
| MCP server pattern | `mcp/app/tools.py` | Tool structure for Phase 3 |
| Health checks | `backend/app/services/healthcheck.py` | Ping/TCP/HTTP patterns |
| Docker Compose | `docker-compose.yml` | Service structure |

---

## 13. Security

- `topology.json` contains management IPs — do not commit to public GitHub
- Credentials can reference env vars: `"credentials": "$SWITCH_PASSWORD"`
- MCP gateway handles auth to devices

---

## 14. Resolved Design Questions

| Question | Resolution |
|----------|-----------|
| Port naming | Both: `device_name` (native) + key (alias). MAC is the real identity. |
| Path objects | Not stored. Computed at query time via graph traversal. |
| Dependencies/constraints | Not in V1. VLAN compatibility + MAC verification catches real problems. |
| Trace start point | Explicit source and/or target device required. VLAN-only query returns all carrying components. |
| Bridges/subinterfaces | Treated as logical ports. Same graph traversal. Intra-device hops via `bridge_ports` / `parent_port`. |
| Observation confidence | `source` field: `mcp_live` > `declared` > `inferred` > `unknown`. |
| Expected absence | Verifier checks both: expected MAC missing AND unexpected MAC present. |
| VLAN asymmetry | Renamed to "VLAN compatibility." Subset subscriptions are normal. Mismatched access VLANs are errors. |
| Model authority | `topology.json` is reviewed working truth for V1. Not the forever-architecture. |
| Frontend vs engine | Engine first (Phase 1), UI second (Phase 2). |
| vmbr0 VLAN-aware | Never on frontend. Backend only. |
| Firewall rules | Not in model. Stay in OPNsense. |
| Historical verification | Not in V1. Last result only. |
| Multi-site | Not in V1. Single site. |
