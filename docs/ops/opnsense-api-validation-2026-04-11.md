# OPNsense API Validation — 2026-04-11 07:39 UTC

**Target:** 172.16.0.1
**Tools probed:** 19

## Summary

- **empty**: 13
- **works**: 6

## Results

| # | Tool | Category | Class | Status | Items | Latency |
|---|------|----------|-------|--------|-------|---------|
| 1 | `opnsense-get-interfaces` | interfaces | safe_read | OK | 16 | 1661ms |
| 2 | `opnsense-get-system-status` | system | safe_read | EMPTY | — | 243ms |
| 3 | `opnsense-get-system-health` | system_health | safe_read | EMPTY | — | 94ms |
| 4 | `opnsense-get-system-routes` | routes | safe_read | OK | 1 | 136ms |
| 5 | `opnsense-firewall-get-rules` | firewall_rules | safe_read | EMPTY | 0 | 242ms |
| 6 | `opnsense-get-firewall-aliases` | firewall_aliases | safe_read | OK | 13 | 183ms |
| 7 | `opnsense-nat-get-port-forward-info` | nat | safe_read | OK | — | 36ms |
| 8 | `opnsense-dhcp-list-servers` | dhcp_servers | safe_read | EMPTY | — | 41ms |
| 9 | `opnsense-dhcp-get-leases` | dhcp_leases | safe_read | EMPTY | — | 40ms |
| 10 | `opnsense-dhcp-list-static-mappings` | dhcp_static | safe_read | EMPTY | — | 38ms |
| 11 | `opnsense-dns-resolver-get-settings` | dns_settings | safe_read | EMPTY | — | 38ms |
| 12 | `opnsense-dns-resolver-list-host-overrides` | dns_overrides | safe_read | EMPTY | — | 38ms |
| 13 | `opnsense-get-vpn-connections` | vpn | safe_read | EMPTY | — | 78ms |
| 14 | `opnsense-list-certificates` | certificates | sensitive_read | EMPTY | — | 48ms |
| 15 | `opnsense-list-users` | users | sensitive_read | EMPTY | — | 38ms |
| 16 | `opnsense-list-plugins` | plugins | safe_read | EMPTY | — | 87ms |
| 17 | `opnsense-backup-config` | config_backup | sensitive_read | EMPTY | — | 87ms |
| 18 | `opnsense-list-vlan-interfaces` | vlans | safe_read | OK | 2 | 741ms |
| 19 | `opnsense-list-bridge-interfaces` | bridges | safe_read | OK | 1 | 83ms |

## Errors

- **opnsense-get-system-status**: gateway returned None (empty content or RPC error)
- **opnsense-get-system-health**: gateway returned None (empty content or RPC error)
- **opnsense-dhcp-list-servers**: gateway returned None (empty content or RPC error)
- **opnsense-dhcp-get-leases**: gateway returned None (empty content or RPC error)
- **opnsense-dhcp-list-static-mappings**: gateway returned None (empty content or RPC error)
- **opnsense-dns-resolver-get-settings**: gateway returned None (empty content or RPC error)
- **opnsense-dns-resolver-list-host-overrides**: gateway returned None (empty content or RPC error)
- **opnsense-get-vpn-connections**: gateway returned None (empty content or RPC error)
- **opnsense-list-certificates**: gateway returned None (empty content or RPC error)
- **opnsense-list-users**: gateway returned None (empty content or RPC error)
- **opnsense-list-plugins**: gateway returned None (empty content or RPC error)
- **opnsense-backup-config**: gateway returned None (empty content or RPC error)
