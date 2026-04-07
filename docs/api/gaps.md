<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->
# OPNsense API Gaps — XML-Only Settings

> OPNsense version: **26.1.5**
> Last updated: 2026-04-07
> Source: `api-xml-coverage-matrix.md`, XML probe output

## Purpose

This document lists all OPNsense settings that have **no MVC REST API** and
require either SSH + config.xml manipulation (`lib-opnsense-xml`) or manual
WebGUI configuration. Each gap is tagged with priority and linked to the
WebGUI page where the setting lives.

## Gap Registry

### System Settings (WebGUI: System → Settings)

| Setting page | XML section | Key properties | Priority | Notes |
|---|---|---|---|---|
| General | `system` | hostname, domain, timezone, dnsserver, language | HIGH | Required for every deployment |
| Administration | `system` | webgui (port, protocol, cert), ssh (enabled, port, key-only) | HIGH | Required for initial access |
| Miscellaneous | `system` | powerd_mode, crypto_hardware, pf limits | LOW | Tuning, not required |

### Interface Assignment (WebGUI: Interfaces → Assignments)

| Setting page | XML section | Key properties | Priority | Notes |
|---|---|---|---|---|
| Assignments | `interfaces` | wan.if, lan.if, optX.if | HIGH | Maps physical NICs to logical interfaces |
| Interface config | `interfaces` | ipaddr, subnet, gateway, media, mediaopt | HIGH | IP addressing per interface |
| PPPoE/PPTP | `ppps` | ports, username, password, provider, mtu | MEDIUM | ISP-specific (Proximus VLAN 10) |
| Settings (global) | `OPNsense.Interfaces` | — | LOW | if-settings API returns global but no write |

### Firewall (WebGUI: Firewall → Settings)

| Setting page | XML section | Key properties | Priority | Notes |
|---|---|---|---|---|
| Advanced | `filter`, `system` | optimization, state limits, fragments | LOW | Tuning only |

### Network Services (legacy / pre-26.1)

| Setting page | XML section | Key properties | Priority | Notes |
|---|---|---|---|---|
| DHCP Server (ISC) | `dhcpd` | range, static-map, gateway, DNS | DEPRECATED | Replaced by Kea DHCP (API: `kea4-*`) |
| DHCPv6 Server (ISC) | `dhcpdv6` | range6, static-map | DEPRECATED | Replaced by Kea DHCPv6 (API: `kea6-*`) |
| NTP (ntpd) | `ntpd` | server, orphan | DEPRECATED | Replaced by Chrony plugin (API available) |
| dnsmasq | `dnsmasq` | host, domain, address | DEPRECATED | Replaced by Dnsmasq MVC (API: `dnsmasq-*`) |
| SNMP | `snmpd` | community, location, contact | LOW | Rarely needed |

### HA / Clustering

| Setting page | XML section | Key properties | Priority | Notes |
|---|---|---|---|---|
| HA Sync | `hasync` | pfsyncenabled, synchronizetoip, username, password | LOW | Not in PoC scope |

### Other XML-only

| Setting page | XML section | Key properties | Priority | Notes |
|---|---|---|---|---|
| Bridge | `bridges` | bridgeif, members | LOW | API `if-bridge` covers MVC bridges |
| GIF tunnels | `gifs` | gifif, remote-addr | LOW | API `if-gif` covers MVC |
| GRE tunnels | `gres` | greif, remote-addr | LOW | API `if-gre` covers MVC |
| LAGG/bond | `laggs` | laggif, members, proto | LOW | API `if-lagg` covers MVC |
| Wireless | `wireless` | — | NONE | Not applicable |
| RRD | `rrd` | — | NONE | Graph data, not config |

## Action Plan

1. **HIGH priority gaps** (system general, administration, interface assignment):
   - Handled via conf.iso seed config for initial deployment
   - Post-install changes: WebGUI only (no automation path yet)
   - Tracked in: `lib-opnsense` GitHub issues (to be created per gap)

2. **DEPRECATED gaps** (ISC DHCP, ntpd, dnsmasq legacy):
   - OPNsense 26.1+ ships Kea DHCP and Chrony with full MVC API
   - DO NOT build XML managers for deprecated services
   - Use API managers: `kea4-*`, `kea6-*`, `chrony-*`, `dnsmasq-*`

3. **LOW/NONE gaps**: no action planned, document only

## References

- Full coverage matrix: `archive/xml/api-xml-coverage-matrix.md` (archived)
- XML probe data: `archive/xml/xml-config-probe/26.1.5/` (archived)
- ADR-0029: lib-opnsense-api scope (MVC API only)
- ADR-0031: XML-only settings scope (parked — no automation path yet)
