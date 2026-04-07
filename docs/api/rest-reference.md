<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->
# OPNsense REST API Reference — Firewall Control Surface

## Scope
This document is the consolidated per-topic REST API reference for controlling OPNsense as a firewall appliance.

Target platform:
- **OPNsense 26.1.5** (upgraded 25.1.12 → 25.7 → 26.1.5 on 2026-04-05)
- **Minimum version: 26.1** — versions before 26.1 are missing D-NAT, interface settings, and other MVC controllers

Authoritative probe data lives in:
- `lib-opnsense/docs/api/data/{version}/` — versioned JSON per OPNsense release (cross-repo)
- [schema-audit.md](schema-audit.md) — generated .md audit (ground-truth)

This file consolidates:
- routes / endpoints
- per-topic control surface
- field names
- enum values
- value types (`string`, `int-like string`, `enum`, `list`, `dict`)
- known gaps / non-existent routes
- automation implications per domain

---

## Position in the OPNsense refactor

This file is the **deep contract/reference layer** for OPNsense.

Use it to answer:
- what exact fields exist
- which fields are required or important
- how read/write shapes differ
- where type quirks exist
- where apply/reconfigure behavior matters
- where automation should use upstream modules vs a custom wrapper

This file should be richer than `api-route-catalog.md` and more technical than `capability-truth-matrix.md`.

---

## Audit rules for this file

When enriching or reviewing this file:

1. product/API truth comes before library truth
2. document field contracts honestly — do not invent payloads for completeness
3. separate proven facts from inferred facts
4. note when read shape differs from write shape
5. note when a follow-up `reconfigure` / `apply` / service action is required
6. note when current upstream/community Ansible support is weak, broken, or incomplete
7. prefer custom API-backed wrapper guidance over vague “unsupported” claims when the product route clearly exists

---

## Domain evidence model

Each domain in this file should be interpreted with the following confidence levels:
- `DOC` — documented from official docs or local route catalog
- `UI_OBSERVED` — confirmed from WebUI network behavior
- `LIVE_TESTED` — confirmed by direct request against a live OPNsense instance
- `INFERRED` — likely, but not fully confirmed yet

At the moment, this file is a mixed-source engineering reference and should be refined toward higher live-evidence density over time.

---

## Standard automation interpretation

For every domain, read the contract with these questions in mind:
1. does full CRUD exist?
2. is there a separate apply/reconfigure step?
3. can the domain be reconciled idempotently?
4. is ordering significant?
5. are there read/write shape mismatches?
6. can an upstream module handle this cleanly?
7. if not, should we implement a custom API-backed wrapper?

---

## Important API Conventions

### 1. Most booleans are strings
Common pattern:
- `"1"` = enabled / true
- `"0"` = disabled / false

Type should be treated as:
- **string-bool**

### 2. Most integers are also strings
Examples:
- port: `"443"`
- prefix: `"24"`
- sequence: `"1"`
- keepalive: `"25"`

Type should be treated as:
- **int-like string**

### 3. Many read endpoints return enum dicts
A field that is written as a plain string may be returned as a dict of selectable options.

Example read shape:
```json
{
  "wan": { "value": "WAN", "selected": 1 },
  "lan": { "value": "LAN", "selected": 0 }
}
```

Type should be treated as:
- **enum dict** when reading
- **plain string / selected key** when writing

### 4. Create/update payload top-level keys vary by controller
Examples:
- aliases → `alias`
- filter rules → `rule`
- source NAT → `rule`
- WireGuard server → `server`
- WireGuard peer → `client`
- Kea subnet → `subnet4`
- Unbound forwarder → `dot`
- Unbound host override → `host`

Do not assume a generic body shape.

---

# Topic 1 — Firewall Aliases

## Purpose
Reusable address / network / port / group objects used by firewall and NAT rules.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/firewall/alias/searchItem` | List aliases |
| GET | `/api/firewall/alias/getItem/{uuid}` | Get alias schema / alias by UUID |
| GET | `/api/firewall/alias/getAliasUUID/{name}` | Resolve alias name to UUID |
| POST | `/api/firewall/alias/addItem` | Create alias |
| POST | `/api/firewall/alias/setItem/{uuid}` | Update alias |
| POST | `/api/firewall/alias/delItem/{uuid}` | Delete alias |
| POST | `/api/firewall/alias/reconfigure` | Apply alias changes |

## Main fields

| Field | Type | Notes |
|---|---|---|
| `enabled` | string-bool | `"1"` / `"0"` |
| `name` | string | `[a-zA-Z0-9_]`, no dashes/spaces |
| `type` | enum | See alias types |
| `proto` | enum | `IPv4`, `IPv6` |
| `interface` | enum | `""`, `lan`, `wan`, `opt1`... |
| `counters` | string-bool | Enable counters |
| `updatefreq` | int-like string | Used for URL types |
| `content` | string when writing / dict when reading | newline-separated on write |
| `password` | string | URL auth |
| `username` | string | URL auth |
| `authtype` | enum | `""`, `Basic`, `Bearer` |
| `categories` | list | category UUIDs |
| `description` | string | free text |

## Alias type enum

| Key | Label |
|---|---|
| `host` | Host(s) |
| `network` | Network(s) |
| `port` | Port(s) |
| `url` | URL (IPs) |
| `urltable` | URL Table (IPs) |
| `urljson` | URL Table in JSON format (IPs) |
| `geoip` | GeoIP |
| `networkgroup` | Network group |
| `mac` | MAC address |
| `asn` | BGP ASN |
| `dynipv6host` | Dynamic IPv6 Host |
| `authgroup` | OpenVPN group |
| `internal` | Internal (automatic) |
| `external` | External (advanced) |

## Notes
- `content` is a **string** on write, newline-separated.
- system aliases exist and are read-only.

## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/firewall-aliases.md`

---

# Topic 2 — Firewall Filter Rules

## Purpose
Core packet-filter policy: pass / block / reject rules on WAN/LAN/OPT/WireGuard.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/firewall/filter/searchRule` | List rules |
| GET | `/api/firewall/filter/getRule` | Empty rule schema |
| GET | `/api/firewall/filter/getRule/{uuid}` | Get specific rule |
| POST | `/api/firewall/filter/addRule` | Create rule |
| POST | `/api/firewall/filter/setRule/{uuid}` | Update rule |
| POST | `/api/firewall/filter/delRule/{uuid}` | Delete rule |
| POST | `/api/firewall/filter/apply` | Apply rule changes |

## Main fields

| Field | Type | Enum / Notes |
|---|---|---|
| `enabled` | string-bool | `"1"` / `"0"` |
| `sequence` | int-like string | Lower = higher priority |
| `action` | enum | `pass`, `block`, `reject` |
| `quick` | string-bool | usually `"1"` |
| `interface` | enum | `wan`, `lan`, `opt1`, `opt2`, `opt3`, `wireguard`, ... |
| `interfacenot` | string-bool | negate interface |
| `direction` | enum | `in`, `out` |
| `ipprotocol` | enum | `inet`, `inet6`, `inet46` |
| `protocol` | enum | `any`, `TCP`, `UDP`, `ICMP`, etc. |
| `source_net` | string | alias, CIDR, IP, or `any` |
| `source_not` | string-bool | negate source |
| `source_port` | string | port / alias |
| `destination_net` | string | alias, CIDR, IP, or `any` |
| `destination_not` | string-bool | negate destination |
| `destination_port` | string | port / alias |
| `gateway` | enum | `""`, `GW_vmbrWAN3`, `Null4`, `Null6` |
| `replyto` | enum | gateway |
| `disablereplyto` | string-bool | disable reply-to |
| `statetype` | enum | `keep`, `sloppy`, `modulate`, `synproxy`, `none` |
| `state-policy` | enum | `""`, `if-bound`, `floating` |
| `log` | string-bool | log hits |
| `allowopts` | string-bool | allow IP options |
| `nosync` | string-bool | disable XMLRPC sync |
| `nopfsync` | string-bool | disable pfsync |
| `statetimeout` | int-like string | custom state timeout |
| `max-src-nodes` | int-like string | limit |
| `max-src-states` | int-like string | limit |
| `max-src-conn` | int-like string | limit |
| `max` | int-like string | max total states |
| `max-src-conn-rate` | int-like string | rate count |
| `max-src-conn-rates` | int-like string | rate interval |
| `overload` | enum | overload table |
| `adaptivestart` | int-like string | adaptive timeout |
| `adaptiveend` | int-like string | adaptive timeout |
| `prio` | enum | `""`, `0`–`7` |
| `set-prio` | enum | `""`, `0`–`7` |
| `set-prio-low` | enum | `""`, `0`–`7` |
| `tag` | string | apply PF tag |
| `tagged` | string | match PF tag |
| `tcpflags1` | enum dict | `syn`, `ack`, `fin`, `rst`, `psh`, `urg`, `ece`, `cwr` |
| `tcpflags2` | enum dict | mask set |
| `categories` | list | category UUIDs |
| `sched` | enum | schedule name |
| `tos` | enum | `lowdelay`, `critical`, `inetcontrol`, `netcontrol` |
| `shaper1` | enum | in-queue |
| `shaper2` | enum | out-queue |
| `description` | string | free text |

## Notes
- `description` is currently the repo idempotency key, but that is weak.
- there is a local claim that `ansibleguy.opnsense.rule` is not sufficient for the current 25.1 firewall-rule use case, but this must be treated as an implementation finding to verify, not as official product truth.
- direct `uri` usage is the safer current path for now.
- **Automation recommendation:** treat firewall rules as `CUSTOM_WRAPPER` territory until a stable managed-key reconciliation model is implemented or upstream module behavior is proven sufficient.
- **Evidence level:** mixed `DOC` + local probe evidence; elevate to `LIVE_TESTED` for exact reconciliation semantics and module-behavior validation.

## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/firewall-rules.md`

---

# Topic 3 — Source NAT / Outbound NAT

## Purpose
Masquerade / no-NAT policy for egressing traffic.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET or POST | `/api/firewall/source_nat/searchRule` | List NAT rules |
| GET | `/api/firewall/source_nat/getRule` | Empty schema |
| GET | `/api/firewall/source_nat/getRule/{uuid}` | Specific rule |
| POST | `/api/firewall/source_nat/addRule` | Create rule |
| POST | `/api/firewall/source_nat/setRule/{uuid}` | Update rule |
| POST | `/api/firewall/source_nat/delRule/{uuid}` | Delete rule |
| POST | `/api/firewall/source_nat/apply` | Apply changes |

## Main fields

| Field | Type | Enum / Notes |
|---|---|---|
| `enabled` | string-bool | `"1"` / `"0"` |
| `nonat` | string-bool | `"1"` = no NAT exclusion |
| `sequence` | int-like string | lower = higher priority |
| `interface` | enum | `lan`, `wan`, `opt1`... |
| `ipprotocol` | enum | `inet`, `inet6` |
| `protocol` | enum | `any`, `TCP`, `UDP`, `ICMP`, etc. |
| `source_net` | string | alias, CIDR, IP, or `any` |
| `source_not` | string-bool | negate source |
| `source_port` | string | optional |
| `destination_net` | string | alias, CIDR, IP, or `any` |
| `destination_not` | string-bool | negate destination |
| `destination_port` | string | optional |
| `target` | string | `wanip`, `lanip`, or explicit IP |
| `target_port` | string | static port translation |
| `log` | string-bool | enable logging |
| `categories` | list | category UUIDs |
| `description` | string | free text |

## Notes
- Correct controller is `source_nat`, not `nat` or `nat_outbound`.
- automatic/hybrid/manual mode switching was not confirmed via REST.
- **Automation recommendation:** use `CUSTOM_WRAPPER` until NAT mode handling and ordering/apply semantics are live-validated.
- **Evidence level:** `DOC` + local probe notes, not yet fully `LIVE_TESTED`.
## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/source-nat.md`

---

# Topic 4 — Interfaces, VLANs, and Interface Assignment

## Purpose
Layer-3 / interface control surface: VLAN subinterfaces, IPs, interface bindings.

## Endpoints

### VLAN settings
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/interfaces/vlan_settings/searchItem` | List VLANs |
| GET | `/api/interfaces/vlan_settings/getItem/{uuid}` | VLAN by UUID |
| POST | `/api/interfaces/vlan_settings/addItem` | Create VLAN |
| POST | `/api/interfaces/vlan_settings/setItem/{uuid}` | Update VLAN |
| POST | `/api/interfaces/vlan_settings/delItem/{uuid}` | Delete VLAN |
| POST | `/api/interfaces/vlan_settings/reconfigure` | Apply VLAN changes |

### Interface overview / config
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/interfaces/overview/interfacesInfo` | Live interface overview |
| POST | `/api/interfaces/overview/setInterfaceConfig/{identifier}` | Set interface IP config |

### Interface settings / assignments
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/interfaces/settings/addInterface` | Expected assignment create route, but observed 404 on 25.1 |
| POST | `/api/interfaces/settings/setInterface/{identifier}` | Configure assigned interface |

## VLAN fields

| Field | Type | Notes |
|---|---|---|
| `if` | enum | parent interface (`vtnet1`, etc.) |
| `tag` | int-like string | VLAN ID |
| `pcp` | enum | `0`–`7` |
| `proto` | enum | `""`, `802.1q`, `802.1ad` |
| `descr` | string | description |
| `vlanif` | string | read-only kernel device name |

## Interface config fields

| Field | Type | Notes |
|---|---|---|
| `type` | enum | e.g. `staticv4` |
| `ipaddr` | string | IPv4 address |
| `subnet` | int-like string | prefix length |
| `gateway` | string | gateway key |

## Assigned interface fields

| Field | Type | Notes |
|---|---|---|
| `enable` | string-bool | `"1"` / `"0"` |
| `ipaddr` | string | IP |
| `subnet` | int-like string | prefix |
| `blockpriv` | string-bool | block private nets |
| `blockbogons` | string-bool | block bogons |

## Critical gap
- `/api/interfaces/settings/addInterface` is documented as desired behavior but observed **404** on OPNsense 25.1.
- `/api/interfaces/assignments/searchItem` also returns **404**.
- **Automation recommendation:** keep interface assignment as an explicit `EXCEPTION` until disproven by live WebUI/API inspection.
- **Evidence level:** local probe evidence indicates real uncertainty remains here.
## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/interfaces-vlans.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/gaps.md`

---

# Topic 5 — Routes / Gateways

## Purpose
Static routes and route reconfigure.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/routes/routes/searchRoute` | List routes |
| GET | `/api/routes/routes/getRoute` | Empty route schema |
| POST | `/api/routes/routes/addRoute` | Create route |
| POST | `/api/routes/routes/delRoute/{uuid}` | Delete route |
| POST | `/api/routes/routes/reconfigure` | Apply route changes |

## Fields

| Field | Type | Notes |
|---|---|---|
| `network` | string | CIDR |
| `gateway` | enum dict / string key | e.g. `GW_vmbrWAN3` |
| `descr` | string | description |
| `disabled` | string-bool | `"0"` / `"1"` |

## Notes
- standalone gateway management endpoints were not confirmed.
- gateway choices appear via schema enum.

## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/system.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/gaps.md`

---

# Topic 6 — System Identity, Firmware, Diagnostics, Syslog

## Purpose
Core platform status, system metadata, firmware state, logs.

## Endpoints

### Firmware / product
| Method | Path | Purpose |
|---|---|---|
| GET or POST | `/api/core/firmware/status` | Firmware status |
| GET | `/api/core/firmware/running` | Task running state |
| GET | `/api/core/firmware/info` | Package / firmware info |

### System diagnostics
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/diagnostics/system/systemInformation` | Host identity |
| GET | `/api/diagnostics/system/systemResources` | Memory/resources |
| GET | `/api/diagnostics/system/systemTime` | Time/load |
| GET | `/api/core/system/status` | System dashboard status |

### Syslog
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/syslog/settings/get` | Syslog config |

### General settings
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/core/system/general` | One-shot write path for hostname/domain/timezone (POST-only candidate) |

## System / syslog fields

### firmware/status key fields
| Field | Type | Notes |
|---|---|---|
| `status` | string | e.g. `error`, `ok` |
| `status_msg` | string | human message |
| `product.product_version` | string | version |
| `product.product_abi` | string | ABI |
| `product.product_mirror` | string | package mirror |

### systemResources
| Field | Type | Notes |
|---|---|---|
| `memory.total` | string | bytes |
| `memory.used` | int | bytes |
| `memory.total_frmt` | string | MiB |
| `memory.used_frmt` | string/int | MiB |

### systemTime
| Field | Type | Notes |
|---|---|---|
| `uptime` | string | HH:MM:SS |
| `datetime` | string | current time |
| `config` | string | last config save |
| `loadavg` | string | 1/5/15 load |

### syslog/settings/get
| Field | Type | Notes |
|---|---|---|
| `general.enabled` | string-bool | syslog enabled |
| `general.loglocal` | string-bool | local logging |
| `general.maxpreserve` | int-like string | days |
| `general.maxfilesize` | int-like string / empty | max MB |
| `destinations.destination` | list | remote targets |

## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/system.md`

---

# Topic 7 — Unbound DNS Resolver

## Purpose
DNS resolver service, host overrides, forwarders, DoT.

## Endpoints

### Settings
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/unbound/settings/get` | Full config |
| POST | `/api/unbound/settings/set` | Update general settings |
| GET | `/api/unbound/settings/searchForward` | List forwarders |
| GET | `/api/unbound/settings/getForward` | Empty forwarder schema |
| GET | `/api/unbound/settings/getForward/{uuid}` | Specific forwarder |
| POST | `/api/unbound/settings/addForward` | Create forwarder |
| POST | `/api/unbound/settings/setForward/{uuid}` | Update forwarder |
| POST | `/api/unbound/settings/delForward/{uuid}` | Delete forwarder |
| GET | `/api/unbound/settings/searchHostOverride` | List host overrides |
| GET | `/api/unbound/settings/getHostOverride` | Empty host schema |
| GET | `/api/unbound/settings/getHostOverride/{uuid}` | Specific host override |
| POST | `/api/unbound/settings/addHostOverride` | Create host override |
| POST | `/api/unbound/settings/setHostOverride/{uuid}` | Update host override |
| POST | `/api/unbound/settings/delHostOverride/{uuid}` | Delete host override |
| GET | `/api/unbound/settings/searchHostAlias` | List host aliases |
| GET | `/api/unbound/settings/getHostAlias` | Empty alias schema |
| POST | `/api/unbound/settings/addHostAlias` | Create host alias |
| POST | `/api/unbound/settings/setHostAlias/{uuid}` | Update host alias |
| POST | `/api/unbound/settings/delHostAlias/{uuid}` | Delete host alias |
| POST | `/api/unbound/settings/reconfigure` | Apply changes |

### Service
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/unbound/service/status` | Service status |
| POST | `/api/unbound/service/start` | Start |
| POST | `/api/unbound/service/stop` | Stop |
| POST | `/api/unbound/service/restart` | Restart |

## Key fields

### general section
| Field | Type | Notes |
|---|---|---|
| `enabled` | string-bool | enable Unbound |
| `port` | int-like string | usually `53` |
| `stats` | string-bool | stats enabled |
| `active_interface` | enum dict | listening interfaces |
| `dnssec` | string-bool | DNSSEC |
| `dns64` | string-bool | DNS64 |
| `dns64prefix` | string | prefix |
| `regdhcp` | string-bool | register DHCP leases |
| `regdhcpdomain` | string-bool / string | DHCP domain behavior |
| `regdhcpstatic` | string-bool | register DHCP static mappings |
| `noreglladdr6` | string-bool | disable link-local register |
| `txtsupport` | string-bool | TXT support |
| `cacheflush` | string-bool | flush cache on reload |
| `local_zone_type` | enum | `transparent`, `always_nxdomain`, `always_refuse`, `deny`, `refuse`, `static`, `typetransparent` |
| `outgoing_interface` | enum dict | outgoing interfaces |
| `enable_wpad` | string-bool | WPAD |

### advanced section key fields
| Field | Type | Notes |
|---|---|---|
| `hideidentity` | string-bool | hide identity |
| `hideversion` | string-bool | hide version |
| `prefetch` | string-bool | prefetch |
| `aggressivensec` | string-bool | aggressive NSEC |
| `serveexpired` | string-bool | serve expired |
| `logqueries` | string-bool | log queries |
| `logreplies` | string-bool | log replies |
| `logverbosity` | enum/string | log level |
| `privateaddress` | list/string | private ranges |

### DoT / forwarder fields
| Field | Type | Notes |
|---|---|---|
| `enabled` | string-bool | enable |
| `type` | enum | `dot`, `forward` |
| `domain` | string | scope |
| `server` | string | IP or hostname |
| `port` | int-like string | e.g. `853` |
| `verify` | string | TLS verify hostname |
| `forward_tcp_upstream` | string-bool | force TCP |
| `description` | string | description |

### host override fields
| Field | Type | Notes |
|---|---|---|
| `enabled` | string-bool | enable |
| `hostname` | string | short name |
| `domain` | string | domain |
| `rr` | enum | `A`, `AAAA`, `MX` |
| `mxprio` | int-like string | MX priority |
| `mx` | string | MX server |
| `server` | string | IP for A/AAAA |
| `description` | string | description |

## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/unbound-dns.md`

---

# Topic 8 — Kea DHCPv4

## Purpose
Modern DHCPv4 control plane in OPNsense 25.1.

## Endpoints

### Global DHCPv4
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/kea/dhcpv4/get` | Get global settings |
| POST | `/api/kea/dhcpv4/set` | Set global settings |
| GET | `/api/kea/dhcpv4/searchSubnet` | List subnets |
| GET | `/api/kea/dhcpv4/getSubnet` | Empty subnet schema |
| GET | `/api/kea/dhcpv4/getSubnet/{uuid}` | Specific subnet |
| POST | `/api/kea/dhcpv4/addSubnet` | Create subnet |
| POST | `/api/kea/dhcpv4/setSubnet/{uuid}` | Update subnet |
| POST | `/api/kea/dhcpv4/delSubnet/{uuid}` | Delete subnet |
| GET | `/api/kea/dhcpv4/searchReservation` | List reservations |
| GET | `/api/kea/dhcpv4/getReservation` | Empty reservation schema |
| GET | `/api/kea/dhcpv4/getReservation/{uuid}` | Specific reservation |
| POST | `/api/kea/dhcpv4/addReservation` | Create reservation |
| POST | `/api/kea/dhcpv4/setReservation/{uuid}` | Update reservation |
| POST | `/api/kea/dhcpv4/delReservation/{uuid}` | Delete reservation |
| POST | `/api/kea/dhcpv4/reconfigure` | Apply changes |

### Service / control agent / leases
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/kea/service/status` | Service status |
| POST | `/api/kea/service/start` | Start |
| POST | `/api/kea/service/stop` | Stop |
| POST | `/api/kea/service/restart` | Restart |
| GET | `/api/kea/ctrl_agent/get` | Control agent config |
| POST | `/api/kea/ctrl_agent/set` | Control agent config update |
| POST | `/api/kea/leases4/search` | Search active leases |

## Global fields

| Field | Type | Notes |
|---|---|---|
| `general.enabled` | string-bool | enable DHCPv4 |
| `general.interfaces` | enum dict | selected interfaces |
| `general.valid_lifetime` | int-like string | lease seconds |
| `general.fwrules` | string-bool | auto DHCP fw rules |
| `general.dhcp_socket_type` | enum | `udp`, `raw` |
| `ha.enabled` | string-bool | HA mode |
| `ha.this_server_name` | string | HA server name |
| `ha.max_unacked_clients` | int-like string | HA threshold |

## Subnet fields

| Field | Type | Notes |
|---|---|---|
| `subnet` | string | CIDR |
| `next_server` | string | PXE/TFTP |
| `option_data_autocollect` | string-bool | auto collect options |
| `option_data.domain_name_servers` | enum dict | DNS servers |
| `option_data.domain_search` | enum dict | search domains |
| `option_data.routers` | enum dict | gateways |
| `option_data.static_routes` | string | option 121 |
| `option_data.domain_name` | string | DHCP domain |
| `option_data.ntp_servers` | enum dict | NTP servers |
| `option_data.time_servers` | string | time servers |
| `option_data.tftp_server_name` | string | PXE |
| `option_data.boot_file_name` | string | PXE boot file |
| `match-client-id` | string-bool | client-id behavior |
| `pools` | string | ranges, newline-separated |
| `description` | string | description |

## Reservation fields

| Field | Type | Notes |
|---|---|---|
| `subnet` | list | subnet UUID list |
| `ip_address` | string | reserved IP |
| `hw_address` | string | MAC |
| `hostname` | string | hostname |
| `description` | string | description |

## Notes
- Kea is the right path for new DHCP automation on 25.1.
- old ISC routes are partial / legacy only.
- **Automation recommendation:** `CUSTOM_WRAPPER` on top of Kea endpoints is the preferred current direction.
- **Evidence level:** route coverage is strong; end-to-end payload/apply validation should be pushed to `LIVE_TESTED`.
## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/kea-dhcpv4.md`

---

# Topic 9 — WireGuard

## Purpose
VPN server instances, peers, and service control.

## Endpoints

### Server instances
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/wireguard/server/searchServer` | List servers |
| GET | `/api/wireguard/server/getServer` | Empty server schema |
| GET | `/api/wireguard/server/getServer/{uuid}` | Specific server |
| POST | `/api/wireguard/server/addServer` | Create server |
| POST | `/api/wireguard/server/setServer/{uuid}` | Update server |
| POST | `/api/wireguard/server/delServer/{uuid}` | Delete server |

### Peers / clients
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/wireguard/client/searchClient` | List peers |
| GET | `/api/wireguard/client/getClient` | Empty peer schema |
| GET | `/api/wireguard/client/getClient/{uuid}` | Specific peer |
| POST | `/api/wireguard/client/addClient` | Create peer |
| POST | `/api/wireguard/client/setClient/{uuid}` | Update peer |
| POST | `/api/wireguard/client/delClient/{uuid}` | Delete peer |

### Service
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/wireguard/service/reconfigure` | Apply changes |
| POST | `/api/wireguard/service/start` | Start |
| POST | `/api/wireguard/service/stop` | Stop |
| POST | `/api/wireguard/service/restart` | Restart |
| POST | `/api/wireguard/service/show` | Status / handshakes |

## Server fields

| Field | Type | Notes |
|---|---|---|
| `enabled` | string-bool | enable |
| `name` | string | instance name |
| `instance` | int-like string | `0` => `wg0` |
| `pubkey` | string | read-only public key |
| `privkey` | string | sensitive private key |
| `port` | int-like string | UDP port |
| `mtu` | int-like string | MTU |
| `dns` | enum dict | optional DNS |
| `tunneladdress` | string on write / dict on read | e.g. `10.99.0.1/24` |
| `disableroutes` | string-bool | disable auto routes |
| `gateway` | string | optional |
| `carp_depend_on` | enum dict | HA dependency |
| `peers` | dict | selected peer UUIDs |
| `endpoint` | string | optional endpoint |
| `peer_dns` | string | DNS pushed to peers |

## Peer fields

| Field | Type | Notes |
|---|---|---|
| `enabled` | string-bool | enable |
| `name` | string | peer name |
| `pubkey` | string | peer public key |
| `psk` | string | optional pre-shared key |
| `tunneladdress` | string on write / dict on read | e.g. `10.99.0.2/32` |
| `serveraddress` | string | remote server address |
| `serverport` | int-like string | remote port |
| `endpoint` | string | `host:port` |
| `keepalive` | int-like string | e.g. `25` |
| `servers` | dict | selected server UUIDs |

## Notes
- `ansibleguy.opnsense.wireguard_peer` has a keepalive parsing issue on 25.1.
- direct `uri` is safer for peer CRUD.
- **Automation recommendation:** `CUSTOM_WRAPPER` for server/peer reconciliation until upstream behavior is proven clean.
- **Evidence level:** route and field coverage are strong; update/delete/apply semantics still need live confirmation.
## Probe source
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/wireguard.md`

---

# Topic 10 — Missing / Broken / Not Confirmed Routes

> **Verified:** 2026-04-05 via live probe against OPNsense **26.1.5**
> Full probe results: `schema-audit.md` (200 endpoints)

## Category 1 — MVC not yet migrated on 25.1

These controllers have **no MVC API** on 26.1. Interface assignment and system
settings remain legacy PHP. Requires SSH + config.xml or conf.iso seed.

| Route / area | Status on 26.1 | Explanation |
|---|---|---|
| `/api/interfaces/settings/addInterface` | 404 | Interface assignment creation — legacy PHP. No REST path. |
| `/api/interfaces/assignments/searchItem` | 404 | Interface assignment listing — legacy PHP. No REST path. |
| `/api/interfaces/settings/reconfigure` | 404 | Interface settings reconfigure — legacy PHP. |
| `/api/system/general/*` | N/A | System general (hostname, domain, DNS) — no API. |
| `/api/system/administration/*` | N/A | System admin (SSH, WebGUI) — no API. |

See [gaps.md](gaps.md) for the full XML-only gap registry.

## Category 2 — Fixed in 26.1 (were gaps on 25.1)

These controllers now work on 26.1+:

| Route / area | 25.1 status | 26.1 status |
|---|---|---|
| `/api/firewall/d_nat/*` | 404 | **200 OK** — full CRUD |
| `/api/firewall/source_nat/*` | 404 | **200 OK** — full CRUD |
| `/api/firewall/one_to_one/*` | 404 | **200 OK** — full CRUD |
| `/api/firewall/npt/*` | 404 | **200 OK** — full CRUD |
| `/api/firewall/filter/*` | 404 | **200 OK** — full CRUD |
| `/api/firewall/filter_base/*` | 404 | Still 404 — use `/api/firewall/filter/apply` directly |

## Category 3 — Plugin not installed (install to unlock)

| Route / area | Status | Plugin needed |
|---|---|---|
| `/api/dnsmasq/*` (15 endpoints) | 404 | `os-dnsmasq-maas` — not needed (we use Kea + Unbound) |
| `/api/radvd/*` (4 endpoints) | 404 | `os-radvd` — install if IPv6 RA needed |
| `/api/captiveportal/service/status` | 404 | Service not started |

## Category 4 — Deprecated / replaced

| Route / area | Status | Replacement |
|---|---|---|
| `/api/ntpd/*` | N/A | **Chrony plugin** — install `os-chrony`, API available |
| `/api/dhcpv4/server/*` (ISC) | N/A | **Kea DHCP** — `/api/kea/dhcpv4/*` (built-in on 26.1) |
| `/api/dhcpv6/server/*` (ISC) | N/A | **Kea DHCPv6** — `/api/kea/dhcpv6/*` |

## Category 5 — Wrong path (corrected)

| Wrong path | Correct path | Note |
|---|---|---|
| `/api/firewall/nat/...` | `/api/firewall/source_nat/...` | Outbound NAT = `source_nat` controller |
| `/api/firewall/nat_outbound/...` | `/api/firewall/source_nat/...` | Same correction |
| `/api/routes/gateway/searchGateway` | `/api/routing/settings/search_gateway` | Gateway CRUD is under `routing`, not `routes` |
| `/api/diagnostics/system/systemArp` | `/api/diagnostics/interface/get_arp` | ARP is under interface controller |

## Probe source
- [schema-audit.md](schema-audit.md) — live probe (200 endpoints on 26.1.5)
- [gaps.md](gaps.md) — XML-only settings with no API

---

# Topic 11 — Per-Topic Source Files

This consolidated doc was built from:
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/firewall-aliases.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/firewall-rules.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/source-nat.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/interfaces-vlans.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/system.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/unbound-dns.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/kea-dhcpv4.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/wireguard.md`
- `/home/by-systems/.openclaw/workspace/repos/ansible-platform/docs/tools/opnsense/api/gaps.md`

---

# Final Note

This file is a **control-surface index** for OPNsense REST.
It is not yet a proof that **every** OPNsense feature is controllable through REST.

Where the API is missing, this document marks the gap explicitly instead of pretending it exists.
