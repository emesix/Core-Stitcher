---
name: network-diagnostician
description: How to diagnose network issues using Stitch tools + raw OPNsense MCP tools together — systematic troubleshooting workflows
---

# Network Diagnostician Guide

You have two tool layers for diagnosis: **Stitch MCP tools** (domain engine, topology-aware) and **raw OPNsense MCP tools** (direct firewall access via the gateway). This skill teaches you when to use which, and how to combine them into effective troubleshooting workflows.

## Tool inventory

### Layer 1: Stitch tools (topology-aware, structured output)
- `stitch_preflight_run` — declared vs observed verification
- `stitch_trace_vlan` — VLAN path tracing with break detection
- `stitch_impact_preview` — "what breaks if X changes?"
- `stitch_topology_diagnostics` — graph health (dangling ports, orphans)
- `stitch_device_detail` — device + ports
- `stitch_device_neighbors` — adjacency

### Layer 2: OPNsense MCP tools (raw firewall data, via gateway)
These are called directly through the MCP gateway, not through stitch:
- `opnsense-get-interfaces` — live interface status, IPs, counters
- `opnsense-get-firewall-rules` — active firewall ruleset
- `opnsense-get-firewall-logs` — recent blocked/passed traffic
- `opnsense-perform-firewall-audit` — security posture check
- `opnsense-get-system-routes` — routing table
- `opnsense-get-system-health` — CPU, memory, disk, temps
- `opnsense-get-system-status` — version, uptime, pending updates
- `opnsense-dhcp-get-leases` — active DHCP clients
- `opnsense-dhcp-list-static-mappings` — DHCP reservations
- `opnsense-search-logs` — cross-log pattern search
- `opnsense-get-service-logs` — per-service logs
- `opnsense-analyze-security-events` — threat analysis

## Diagnostic workflows

### "Is the network healthy?"

```
1. stitch_preflight_run(detail="standard")
   → Gives declared vs observed verdict
   
2. stitch_topology_diagnostics()
   → Dangling ports, orphans, missing endpoints

3. opnsense-get-system-health
   → CPU, memory, disk — is the firewall itself stressed?

4. opnsense-get-system-status
   → Uptime, pending updates, needs reboot?
```

Report: topology health + firewall health + any pending maintenance.

### "Device X can't reach device Y"

```
1. stitch_device_detail(device_id="X")
   stitch_device_detail(device_id="Y")
   → Are both in the topology? What ports/VLANs?

2. stitch_trace_vlan(vlan=N, source="X", target="Y")
   → Is there a VLAN path? Where does it break?

3. opnsense-get-firewall-rules
   → Is there a rule blocking traffic between X and Y?

4. opnsense-get-firewall-logs(search for X or Y IPs)
   → Are packets being dropped?

5. opnsense-get-system-routes
   → Is there a route to the destination network?
```

### "Why is traffic being blocked?"

```
1. opnsense-get-firewall-logs
   → Look for recent blocked entries, note source/dest/port/rule

2. opnsense-get-firewall-rules
   → Find the matching rule, check if it's intentional

3. opnsense-perform-firewall-audit
   → Broader security posture — any misconfigurations?

4. If the block is between topology devices:
   stitch_trace_vlan(vlan=relevant_vlan)
   → Is the path even supposed to exist?
```

### "What DHCP clients are active?"

```
1. opnsense-dhcp-get-leases
   → Active leases with MAC, IP, hostname

2. opnsense-dhcp-list-static-mappings
   → Reserved addresses

3. opnsense-dhcp-get-lease-statistics
   → Pool utilization
```

### "What changed? Something broke."

```
1. stitch_preflight_run(detail="full")
   → Full verification — compare against declared topology

2. opnsense-search-logs(search_query="error", time_range="1h")
   → Recent errors across all logs

3. opnsense-get-service-logs(service_name="configd")
   → Configuration daemon — was a config change applied?

4. opnsense-get-service-logs(service_name="openvpn")
   or whatever service is suspect
   
5. If you have a previous verification report:
   Run preflight again and compare findings manually
```

### "Is interface X working?"

```
1. stitch_device_detail(device_id="device_with_X")
   → Is the port declared? What's expected?

2. opnsense-get-interfaces
   → Live status: up/down, carrier, counters, IP

3. stitch_device_neighbors(device_id="device_with_X")
   → Who should be connected?

4. stitch_trace_vlan(vlan=N, source="device_with_X")
   → Can traffic flow from this port?
```

### "Security check"

```
1. opnsense-perform-firewall-audit
   → Automated security posture review

2. opnsense-analyze-security-events(time_range="24h")
   → Recent threats, blocked attacks

3. opnsense-get-firewall-rules
   → Review for overly permissive rules

4. opnsense-get-system-status
   → Firmware current? Updates pending?
```

## Combining layers effectively

**Start with Stitch tools** when the question is about topology, connectivity, or "should this work?"
Stitch tools understand the declared network design and can compare against reality.

**Drop to OPNsense tools** when you need:
- Live traffic data (firewall logs, counters)
- System health (CPU, memory, disk)
- Service-specific logs
- DHCP/routing details
- Security analysis

**The pattern:** Stitch tells you what SHOULD be true. OPNsense tells you what IS happening. The gap between them is the diagnosis.

## Rules

1. **Start broad, narrow down.** Don't jump to `search-logs` first. Start with `preflight_run` or `topology_diagnostics` to understand the landscape.

2. **Check the obvious first.** Is the device powered on? Is the interface up? Is there a cable? Before running complex traces.

3. **Partial data is normal.** With only OPNsense online (switches down), many checks will show "device not found." That's expected, not an error.

4. **Don't flood the gateway.** OPNsense MCP tools hit a real firewall. Space out calls. Never run them in parallel — the OPNsense web server can crash under concurrent API load.

5. **Report what you know AND what you don't.** "VLAN 42 path is broken at sw-edge-02:eth3" is useful. "I can't verify this because the switchcraft adapter is offline" is also useful. Don't guess.

6. **Timestamps matter.** When reporting log entries or lease data, include timestamps. "Blocked 5 minutes ago" is actionable. "Blocked at some point" is not.
