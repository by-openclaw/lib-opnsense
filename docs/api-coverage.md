# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense

# API Coverage — lib-opnsense

> Checked = implemented + tested. Unchecked = planned.
> Verified against OPNsense **26.1.5** (minimum version: **26.1**).
> Version compatibility: `../platform-setup/tools/opnsense/docs/api-version-compatibility.md`
> Last updated: 2026-04-05

### Auth (immediate, no reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list users | `AuthUserManager` | `POST /api/auth/user/search` | 25.1 | [x] |
| get user | `AuthUserManager` | `GET /api/auth/user/get/{uuid}` | 25.1 | [x] |
| create user | `AuthUserManager` | `POST /api/auth/user/add` | 25.1 | [x] |
| update user | `AuthUserManager` | `POST /api/auth/user/set/{uuid}` | 25.1 | [x] |
| delete user | `AuthUserManager` | `POST /api/auth/user/del/{uuid}` | 25.1 | [x] |
| ensure user | `AuthUserManager` | (composite) | 25.1 | [x] |
| list groups | `AuthGroupManager` | `POST /api/auth/group/search` | 25.1 | [x] |
| get group | `AuthGroupManager` | `GET /api/auth/group/get/{uuid}` | 25.1 | [x] |
| create group | `AuthGroupManager` | `POST /api/auth/group/add` | 25.1 | [x] |
| update group | `AuthGroupManager` | `POST /api/auth/group/set/{uuid}` | 25.1 | [x] |
| delete group | `AuthGroupManager` | `POST /api/auth/group/del/{uuid}` | 25.1 | [x] |
| ensure group | `AuthGroupManager` | (composite) | 25.1 | [x] |
| list privileges | `AuthPrivManager` | `GET /api/auth/priv/get` | 25.1 | [x] |
| assign privilege | `AuthPrivManager` | `POST /api/auth/priv/set_item/{id}` | 25.1 | [x] |
| ensure privilege | `AuthPrivManager` | (composite) | 25.1 | [x] |
| list API keys | `AuthApiKeyManager` | `POST /api/auth/user/search_api_key/{uid}` | 25.1 | [x] |
| create API key | `AuthApiKeyManager` | `POST /api/auth/user/add_api_key/{uid}` | 25.1 | [x] |
| delete API key | `AuthApiKeyManager` | `POST /api/auth/user/del_api_key/{uid}/{id}` | 25.1 | [x] |
| delete all keys | `AuthApiKeyManager` | (composite) | 25.1 | [x] |

### Firewall — Filter (requires apply)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list filter rules | `FwFilterManager` | `POST /api/firewall/filter/search_rule` | 25.1 | [x] |
| get filter rule | `FwFilterManager` | `GET /api/firewall/filter/get_rule/{uuid}` | 25.1 | [x] |
| ensure filter rule | `FwFilterManager` | (composite) | 25.1 | [x] |
| apply filter | `FwFilterManager` | `POST /api/firewall/filter/apply` | 25.1 | [x] |

### Firewall — NAT D-NAT / Port Forward (requires apply)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list DNAT rules | `FwDnatManager` | `POST /api/firewall/d_nat/search_rule` | **26.1** | [x] |
| get DNAT rule | `FwDnatManager` | `GET /api/firewall/d_nat/get_rule/{uuid}` | **26.1** | [x] |
| ensure DNAT rule | `FwDnatManager` | (composite) | **26.1** | [x] |
| apply DNAT | `FwDnatManager` | `POST /api/firewall/d_nat/apply` | **26.1** | [x] |

### Firewall — NAT Source NAT (requires apply)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list SNAT rules | `FwSourceNatManager` | `POST /api/firewall/source_nat/search_rule` | 25.1 | [x] |
| get SNAT rule | `FwSourceNatManager` | `GET /api/firewall/source_nat/get_rule/{uuid}` | 25.1 | [x] |
| ensure SNAT rule | `FwSourceNatManager` | (composite) | 25.1 | [x] |
| apply SNAT | `FwSourceNatManager` | `POST /api/firewall/source_nat/apply` | 25.1 | [x] |

### Firewall — NAT One-to-One (requires apply)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list 1:1 rules | `FwOneToOneManager` | `POST /api/firewall/one_to_one/search_rule` | 25.1 | [ ] |
| ensure 1:1 rule | `FwOneToOneManager` | (composite) | 25.1 | [ ] |

### Firewall — NAT NPTv6 (requires apply)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list NPT rules | `FwNptManager` | `POST /api/firewall/npt/search_rule` | 25.1 | [ ] |
| ensure NPT rule | `FwNptManager` | (composite) | 25.1 | [ ] |

### Firewall — Aliases (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list aliases | `FwAliasManager` | `POST /api/firewall/alias/search_item` | 25.1 | [x] |
| ensure alias | `FwAliasManager` | (composite) | 25.1 | [x] |

### Firewall — Categories & Groups

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list categories | `FwCategoryManager` | `POST /api/firewall/category/search_item` | 25.1 | [ ] |
| ensure category | `FwCategoryManager` | (composite) | 25.1 | [ ] |
| list groups | `FwGroupManager` | `POST /api/firewall/group/search_item` | 25.1 | [ ] |
| ensure group | `FwGroupManager` | (composite) | 25.1 | [ ] |

### Unbound DNS (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list forwarders | `UbForwardManager` | `POST /api/unbound/settings/search_forward` | 25.1 | [ ] |
| ensure forwarder | `UbForwardManager` | (composite) | 25.1 | [ ] |
| list host overrides | `UbHostOverrideManager` | `POST /api/unbound/settings/search_host_override` | 25.1 | [ ] |
| ensure host override | `UbHostOverrideManager` | (composite) | 25.1 | [ ] |
| list ACLs | `UbAclManager` | `POST /api/unbound/settings/search_acl` | 25.1 | [ ] |
| ensure ACL | `UbAclManager` | (composite) | 25.1 | [ ] |

### Kea DHCPv4 (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list subnets | `KeaSubnetManager` | `POST /api/kea/dhcpv4/search_subnet` | 25.1 | [ ] |
| ensure subnet | `KeaSubnetManager` | (composite) | 25.1 | [ ] |
| list reservations | `KeaReservationManager` | `POST /api/kea/dhcpv4/search_reservation` | 25.1 | [ ] |
| ensure reservation | `KeaReservationManager` | (composite) | 25.1 | [ ] |

### WireGuard (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list servers | `WgServerManager` | `POST /api/wireguard/server/search_server` | 25.1 | [ ] |
| ensure server | `WgServerManager` | (composite) | 25.1 | [ ] |
| list clients | `WgClientManager` | `POST /api/wireguard/client/search_client` | 25.1 | [ ] |
| ensure client | `WgClientManager` | (composite) | 25.1 | [ ] |

### IPsec (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list connections | `IpsecConnManager` | `POST /api/ipsec/connections/search_connection` | 25.1 | [ ] |
| ensure connection | `IpsecConnManager` | (composite) | 25.1 | [ ] |
| list PSKs | `IpsecPskManager` | `POST /api/ipsec/pre_shared_keys/search_item` | 25.1 | [ ] |
| ensure PSK | `IpsecPskManager` | (composite) | 25.1 | [ ] |

### Interfaces (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list VLANs | `IfVlanManager` | `POST /api/interfaces/vlan_settings/search_item` | 25.1 | [ ] |
| ensure VLAN | `IfVlanManager` | (composite) | 25.1 | [ ] |
| get settings | — | `GET /api/interfaces/settings/get` | **26.1** | [ ] |

### Routes / Gateways (requires reconfigure)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list routes | `RtRouteManager` | `POST /api/routes/routes/searchroute` | 25.1 | [ ] |
| ensure route | `RtRouteManager` | (composite) | 25.1 | [ ] |
| list gateways | `RtGatewayManager` | `POST /api/routing/settings/search_gateway` | 25.1 | [ ] |
| ensure gateway | `RtGatewayManager` | (composite) | 25.1 | [ ] |

### IDS / Suricata

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list policies | `IdsPolicyManager` | `POST /api/ids/settings/search_policy` | 25.1 | [ ] |
| ensure policy | `IdsPolicyManager` | (composite) | 25.1 | [ ] |

### Traffic Shaper

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list pipes | `TsPipeManager` | `POST /api/trafficshaper/settings/search_pipes` | 25.1 | [ ] |
| ensure pipe | `TsPipeManager` | (composite) | 25.1 | [ ] |

### Chrony NTP (requires os-chrony plugin)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| get settings | — | `GET /api/chrony/general/get` | **26.1** | [ ] |
| service status | — | `GET /api/chrony/service/status` | **26.1** | [ ] |

### LLDP (requires os-lldpd plugin)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| get settings | — | `GET /api/lldpd/general/get` | **26.1** | [ ] |
| service status | — | `GET /api/lldpd/service/status` | **26.1** | [ ] |

### System (various)

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list syslog destinations | `SyslogDestManager` | `POST /api/syslog/settings/search_destinations` | 25.1 | [ ] |
| ensure syslog destination | `SyslogDestManager` | (composite) | 25.1 | [ ] |
| list cron jobs | `CronJobManager` | `POST /api/cron/settings/search_jobs` | 25.1 | [ ] |
| ensure cron job | `CronJobManager` | (composite) | 25.1 | [ ] |

### Trust / PKI

| Method | Manager | Endpoint | Since | Status |
|--------|---------|----------|-------|:------:|
| list CAs | `TrustCaManager` | `POST /api/trust/ca/search` | 25.1 | [ ] |
| ensure CA | `TrustCaManager` | (composite) | 25.1 | [ ] |
| list certs | `TrustCertManager` | `POST /api/trust/cert/search` | 25.1 | [ ] |
| ensure cert | `TrustCertManager` | (composite) | 25.1 | [ ] |

### Diagnostics (read-only, no manager needed)

| Method | Client direct | Endpoint | Since | Status |
|--------|---------------|----------|-------|:------:|
| system info | `client.get()` | `GET /api/diagnostics/system/system_information` | 25.1 | [x] |
| ARP table | `client.get()` | `GET /api/diagnostics/interface/get_arp` | 25.1 | [x] |
| routing table | `client.get()` | `GET /api/diagnostics/interface/get_routes` | 25.1 | [x] |
| firewall stats | `client.get()` | `GET /api/diagnostics/firewall/stats` | 25.1 | [x] |
| gateway status | `client.get()` | `GET /api/routes/gateway/status` | 25.1 | [x] |
| audit log | `client.search()` | `POST /api/diagnostics/log/core/audit` | 25.1 | [x] |

---

> Full API route catalog: `../platform-setup/tools/opnsense/docs/api-route-catalog.md`
> Full API schema audit: `../platform-setup/tools/opnsense/docs/api-schema-audit.md`
> Version compatibility: `../platform-setup/tools/opnsense/docs/api-version-compatibility.md`
