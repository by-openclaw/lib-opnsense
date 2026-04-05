# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense

# API Coverage — lib-opnsense

> Checked = implemented + tested. Unchecked = planned.
> Verified against OPNsense **25.1.12**.
> Last updated: 2026-04-05

### Auth (immediate, no reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list users | `AuthUserManager` | `POST /api/auth/user/search` | [x] |
| get user | `AuthUserManager` | `GET /api/auth/user/get/{uuid}` | [x] |
| create user | `AuthUserManager` | `POST /api/auth/user/add` | [x] |
| update user | `AuthUserManager` | `POST /api/auth/user/set/{uuid}` | [x] |
| delete user | `AuthUserManager` | `POST /api/auth/user/del/{uuid}` | [x] |
| ensure user | `AuthUserManager` | (composite) | [x] |
| list groups | `AuthGroupManager` | `POST /api/auth/group/search` | [x] |
| get group | `AuthGroupManager` | `GET /api/auth/group/get/{uuid}` | [x] |
| create group | `AuthGroupManager` | `POST /api/auth/group/add` | [x] |
| update group | `AuthGroupManager` | `POST /api/auth/group/set/{uuid}` | [x] |
| delete group | `AuthGroupManager` | `POST /api/auth/group/del/{uuid}` | [x] |
| ensure group | `AuthGroupManager` | (composite) | [x] |
| list privileges | `AuthPrivManager` | `GET /api/auth/priv/get` | [x] |
| assign privilege | `AuthPrivManager` | `POST /api/auth/priv/set_item/{id}` | [x] |
| ensure privilege | `AuthPrivManager` | (composite) | [x] |

### Firewall (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list aliases | `FwAliasManager` | `POST /api/firewall/alias/search_item` | [ ] |
| ensure alias | `FwAliasManager` | (composite) | [ ] |
| list filter rules | `FwRuleManager` | `POST /api/firewall/filter/search_rule` | [ ] |
| ensure filter rule | `FwRuleManager` | (composite) | [ ] |
| list SNAT rules | `FwSnatManager` | `POST /api/firewall/source_nat/search_rule` | [ ] |
| ensure SNAT rule | `FwSnatManager` | (composite) | [ ] |

### Unbound DNS (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list forwarders | `UbForwardManager` | `POST /api/unbound/settings/search_forward` | [ ] |
| ensure forwarder | `UbForwardManager` | (composite) | [ ] |
| list host overrides | `UbHostOverrideManager` | `POST /api/unbound/settings/search_host_override` | [ ] |
| ensure host override | `UbHostOverrideManager` | (composite) | [ ] |

### Kea DHCPv4 (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list subnets | `KeaSubnetManager` | `POST /api/kea/dhcpv4/search_subnet` | [ ] |
| ensure subnet | `KeaSubnetManager` | (composite) | [ ] |
| list reservations | `KeaReservationManager` | `POST /api/kea/dhcpv4/search_reservation` | [ ] |
| ensure reservation | `KeaReservationManager` | (composite) | [ ] |

### WireGuard (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list servers | `WgServerManager` | `POST /api/wireguard/server/search_server` | [ ] |
| ensure server | `WgServerManager` | (composite) | [ ] |
| list clients | `WgClientManager` | `POST /api/wireguard/client/search_client` | [ ] |
| ensure client | `WgClientManager` | (composite) | [ ] |

### Interfaces (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list VLANs | `IfVlanManager` | `POST /api/interfaces/vlan_settings/search_item` | [ ] |
| ensure VLAN | `IfVlanManager` | (composite) | [ ] |

### Routes / Gateways (requires reconfigure)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list routes | `RtRouteManager` | `POST /api/routes/routes/searchroute` | [ ] |
| ensure route | `RtRouteManager` | (composite) | [ ] |
| list gateways | `RtGatewayManager` | `POST /api/routing/settings/search_gateway` | [ ] |
| ensure gateway | `RtGatewayManager` | (composite) | [ ] |

### System (various)

| Method | Manager | Endpoint | Status |
|--------|---------|----------|:------:|
| list syslog destinations | `SyslogDestManager` | `POST /api/syslog/settings/search_destinations` | [ ] |
| ensure syslog destination | `SyslogDestManager` | (composite) | [ ] |
| list cron jobs | `CronJobManager` | `POST /api/cron/settings/search_jobs` | [ ] |
| ensure cron job | `CronJobManager` | (composite) | [ ] |

### Diagnostics (read-only, no manager needed)

| Method | Client direct | Endpoint | Status |
|--------|---------------|----------|:------:|
| system info | `client.get()` | `GET /api/diagnostics/system/system_information` | [x] |
| ARP table | `client.get()` | `GET /api/diagnostics/interface/get_arp` | [x] |
| routing table | `client.get()` | `GET /api/diagnostics/interface/get_routes` | [x] |
| firewall stats | `client.get()` | `GET /api/diagnostics/firewall/stats` | [x] |
| gateway status | `client.get()` | `GET /api/routes/gateway/status` | [x] |


---

> Full API route catalog: `../platform-setup/tools/opnsense/docs/api-route-catalog.md`
> Full API schema audit: `../platform-setup/tools/opnsense/docs/api-schema-audit.md`
