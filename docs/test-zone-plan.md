<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# Test Zone Plan — lib-opnsense Integration Testing

## Network Diagram

```
  Rune VM (10.100.0.101)
  pfSense DMZ (prod)
        │
        │ pfSense routes DMZ ↔ OOB
        │
        ┌──────────┴───────────┐
        │  pfSense01 (prod)    │
        │  10.100.0.1 (DMZ)    │
        │  10.6.224.1 (OOB)    │
        └──────────┬───────────┘
                   │ vmbrWAN3
                   │
  ┌────────────────┴──────────────────────┐
  │       OPNsense test VM (101)          │
  │                                       │
  │  WAN: vtnet1 ── vmbrWAN3             │
  │  LAN: vtnet0 ── vmbrAPPS (trunk)     │
  │    ├── vlan1310 → 10.11.1.1/24 (MGMT)│
  │    ├── vlan1320 → 10.11.2.1/24 (DMZ) │
  │    └── vlan1330 → 10.11.3.1/24 (SVC) │
  └──┬──────────────┬──────────────┬──────┘
     │              │              │
     │ VLAN 1310    │ VLAN 1320    │ VLAN 1330
     │ VNet: tmgmt  │ VNet: tdmz   │ VNet: tsvc
  ┌──┴───────────┐ ┌┴────────────┐ ┌┴─────────────────┐
  │ MGMT Zone    │ │ DMZ Zone    │ │ SVC Zone          │
  │ 10.11.1.0/24 │ │ 10.11.2.0/24│ │ 10.11.3.0/24      │
  │              │ │             │ │                   │
  │ (API access  │ │ LXC webdmz │ │ LXC websrv        │
  │  via WAN)    │ │ 10.11.2.10 │ │ 10.11.3.10        │
  │              │ │ DNAT ←WAN  │ │ internal only     │
  └──────────────┘ └─────────────┘ └───────────────────┘

  Test flow:
  Rune (10.100.0.101) → pfSense → OPNsense WAN (10.6.239.114)
    ├── API: https://10.6.239.114/api/...
    ├── DNAT: curl 10.6.239.114:8080 → webdmz (10.11.2.10)
    └── SSH: ssh -i ~/.ssh/id_ed25519_opnsense root@10.6.239.114
```

## SDN Zone 'test' (offset +1000 from 'poc')

| Zone | Bridge | Node |
|---|---|---|
| `test` | `vmbrAPPS` (same trunk, different VLANs) | `srv-proxmox-poc-01` |

### VLAN Mapping

| Purpose | poc VLAN | poc Subnet | test VLAN | test VNet | test Subnet | test Gateway |
|---|---|---|---|---|---|---|
| MGMT | 310 | 10.1.1.0/24 | 1310 | `tmgmt` | 10.11.1.0/24 | 10.11.1.1 |
| DMZ | 320 | 10.1.2.0/24 | 1320 | `tdmz` | 10.11.2.0/24 | 10.11.2.1 |
| SVC | 330 | 10.1.3.0/24 | 1330 | `tsvc` | 10.11.3.0/24 | 10.11.3.1 |

### SDN Terraform Config

```
Zone: test (VLAN type, bridge=vmbrAPPS)
VNet: tmgmt (tag=1310, subnet=10.11.1.0/24, gw=10.11.1.1)
VNet: tdmz  (tag=1320, subnet=10.11.2.0/24, gw=10.11.2.1)
VNet: tsvc  (tag=1330, subnet=10.11.3.0/24, gw=10.11.3.1)
```

## OPNsense Test VM (VMID 101)

| Interface | Logical | Bridge | Purpose |
|---|---|---|---|
| vtnet0 | LAN | vmbrAPPS (VLAN trunk) | All test zones via sub-interfaces |
| vtnet1 | WAN | vmbrWAN3 | Internet uplink (static 10.6.239.114/20) |

VLAN sub-interfaces created by OPNsense on vtnet0:

| VLAN sub-if | VLAN ID | IP | Zone |
|---|---|---|---|
| vlan1310 | 1310 | 10.11.1.1/24 | MGMT |
| vlan1320 | 1320 | 10.11.2.1/24 | DMZ |
| vlan1330 | 1330 | 10.11.3.1/24 | SVC |

## Test LXCs

### LXC webdmz — DMZ (public-facing via DNAT)

| Field | Value |
|---|---|
| Hostname | `lxc-webdmz-test-01` (ADR-0010) |
| Purpose | Validate DNAT port forwarding from WAN |
| OS | Debian 12 |
| Container | Docker `traefik/whoami` |
| Network | VNet `tdmz` (VLAN 1320), static IP 10.11.2.10/24 |
| Gateway | 10.11.2.1 (OPNsense) |
| Access | root + Rune SSH key |
| Exposed | OPNsense WAN:8080 → 10.11.2.10:80 (DNAT) |
| Test from | Rune VM: `curl http://10.6.239.114:8080` |

### LXC websrv — SVC (internal only)

| Field | Value |
|---|---|
| Hostname | `lxc-websrv-test-01` (ADR-0010) |
| Purpose | Validate inter-zone routing + firewall rules |
| OS | Debian 12 |
| Container | Docker `traefik/whoami` |
| Network | VNet `tsvc` (VLAN 1330), static IP 10.11.3.10/24 |
| Gateway | 10.11.3.1 (OPNsense) |
| Access | root + Rune SSH key |
| Test from | OPNsense SSH: `curl http://10.11.3.10:80` |

---

## Phased Execution Plan

### Phase 0 — Infrastructure (User)

| # | Task | Owner | Depends on | Status |
|---|---|---|---|---|
| 0.1 | Factory reset OPNsense VM 101 | User | — | ✓ done |
| 0.2 | Enable WebGUI + API key (svc-rune) + SSH + Rune pubkey | User | 0.1 | ✓ done |
| 0.3 | Create SDN zone `test` (VLANs 1310/1320/1330 on vmbrAPPS) | Rune | 0.1 | ✓ done (Terraform) |
| 0.4 | OPNsense upgraded to 26.1.5 | User | 0.1 | ✓ done |
| 0.5 | API access confirmed (svc-rune, 10.6.239.114) | Rune | 0.2 | ✓ done |
| 0.6 | SSH access confirmed (root, `id_ed25519_opnsense`) | Rune | 0.2 | ✓ done |
| 0.7 | Create WAN allow rule + disable block private/bogon on WAN | Rune+User | 0.5 | ✓ done |
| 0.8 | Set WAN to static 10.6.239.114/20 | Rune | 0.7 | parked — pfSense ARP issue, using DHCP 10.6.239.114 |
| 0.9 | Create LXC `lxc-webdmz-test-01` on VNet `tdmz` (10.11.2.10) | User | 0.3 | not started |
| 0.10 | Create LXC `lxc-websrv-test-01` on VNet `tsvc` (10.11.3.10) | User | 0.3 | not started |
| 0.11 | Commit `environments/test/` + NIC swap (infra-terraform-proxmox) | Rune | 0.3 | pending |

### Phase 1 — Foundation (Rune)

| # | Task | Depends on | Deliverable | Status |
|---|---|---|---|---|
| 1.1 | Re-probe API on 10.6.239.114 | 0.7 | `docs/api/data/26.1.5/` — 200/200 OK | ✓ done |
| 1.2 | Fix base.py (enum dict + missing field skip) | — | PR with unit tests | not started |
| 1.3 | Update test device boundaries doc | 0.3 | memory updated | not started |

### Phase 2 — Managers (Rune, one domain per PR)

**Per manager workflow:**
1. Scope + use case doc (endpoints, safety boundaries)
2. Manager code
3. Unit tests (CRUD, ensure, check_mode, error handling)
4. Integration tests (live device, `inttest-` prefix)
5. Update api-coverage.md: `UNIT_TEST_PASSED` → `INTEGRATION_TEST_PASSED`
6. PR: file table + test table + endpoints + safety

**Before starting a new manager: scope + use cases must be validated.**

**Per-scope documentation:** See [docs/scopes/](scopes/) for full use cases, diagrams, and BoM per scope.

| # | Domain | Managers | Scope doc | Status |
|---|---|---|---|---|
| 2.1 | Auth | 4 (user, group, priv, api_key) | [auth.md](scopes/auth.md) | DONE |
| 2.2 | Firewall | 8 (alias, filter, dnat, snat, 1:1, npt, category, group) | [firewall.md](scopes/firewall.md) | DONE |
| 2.3 | Interfaces | 9 (vlan, vip, bridge, gif, gre, lagg, loopback, neighbor, vxlan) | [interfaces.md](scopes/interfaces.md) | DONE |
| 2.4 | Routing | 2 (gateway, route) | [routing.md](scopes/routing.md) | DONE |
| 2.5 | DNS (Unbound) | 6 (host override, alias, forward, acl, dot, diagnostics) | [dns.md](scopes/dns.md) | DONE |
| 2.6 | DHCP (Kea) | 5 (v4 subnet, reservation, peer + v6 subnet, reservation) | [dhcp.md](scopes/dhcp.md) | DONE |
| 2.7 | VPN (WG+OVPN+IPsec) | 13 (wg 2, ovpn 1, ipsec 8) | [vpn.md](scopes/vpn.md) | DONE |
| 2.8 | Traffic Shaper | 3 (pipe, queue, rule) | [shaper.md](scopes/shaper.md) | DONE |
| 2.9 | Trust/PKI | 2 (ca, cert) | [trust.md](scopes/trust.md) | DONE |
| 2.10 | Services | 5 (cron, syslog, captive portal, ddns, plugin) | [services.md](scopes/services.md) | DONE |
| 2.11 | IDS/Suricata | 3 (planned) | — | STANDBY |

**Total: 54 managers implemented, 3 standby (IDS).**

---

> **Per-scope details moved to `docs/scopes/`.**
> Each scope file contains: network diagram, manager list, use case tables,
> bill of materials, safety boundaries, sequence diagrams, and test status.
> The sections below (M01–M14) are archived inline for historical reference.

| # | Domain | Manager(s) | Safety | Priority | Status |
|---|---|---|---|---|---|
| 2.1 | Interfaces | IfVlanManager, IfVipManager | CRUD safe — test zone VLANs | HIGH | DONE |
| 2.2 | Routing | RtGatewayManager, RtRouteManager | CRUD safe — test routes | HIGH | absent |
| 2.3 | FW aliases | FwAliasManager | CRUD safe — `inttest-` prefix | DONE | done |
| 2.4 | FW filter | FwFilterManager | CRUD safe — disabled rules | DONE | done |
| 2.5 | FW categories | FwCategoryManager | CRUD safe | DONE | done |
| 2.6 | FW groups | FwGroupManager | CRUD safe | DONE | done |
| 2.7 | FW DNAT | FwDnatManager | CRUD on test zone — **NOT prod WAN** | DONE | done |
| 2.8 | FW SNAT | FwSourceNatManager | CRUD on test zone — **NOT prod WAN** | DONE | done |
| 2.9 | FW 1:1 NAT | FwOneToOneManager | CRUD safe — disabled rules | HIGH | partial |
| 2.10 | FW NPTv6 | FwNptManager | CRUD safe — disabled rules | MEDIUM | absent |
| 2.11 | Unbound DNS | UbForwardManager, UbHostOverrideManager, UbAclManager, UbHostAliasManager, UbDnsblManager | CRUD safe — `.test` domain | HIGH | absent |
| 2.12 | Kea DHCPv4 | Kea4SubnetManager, Kea4ReservationManager, Kea4PeerManager | CRUD safe — test subnets | MEDIUM | absent |
| 2.13 | Kea DHCPv6 | Kea6SubnetManager, Kea6ReservationManager | CRUD safe — test subnets | MEDIUM | absent |
| 2.14 | WireGuard | WgServerManager, WgClientManager | CRUD safe — test peers | MEDIUM | absent |
| 2.15 | Traffic shaper | TsPipeManager (done), TsQueueManager, TsRuleManager | CRUD safe | LOW | partial |
| 2.16 | Syslog | SyslogDestManager | CRUD safe | LOW | absent |
| 2.17 | Cron | CronJobManager | CRUD safe | LOW | absent |
| 2.18 | Trust/PKI | TrustCaManager, TrustCertManager | CRUD safe — test certs | LOW | absent |
| 2.19 | IPsec | IpsecConnManager, IpsecPskManager, IpsecChildManager, IpsecLocalManager, IpsecRemoteManager, IpsecPoolManager, IpsecKeypairManager, IpsecVtiManager | CRUD safe — test tunnels | LOW | absent |
| 2.20 | IDS | IdsPolicyManager, IdsPolicyRuleManager, IdsUserRuleManager | CRUD safe | LOW | absent |
| 2.21 | Interfaces (extra) | IfBridgeManager, IfGifManager, IfGreManager, IfLaggManager, IfLoopbackManager, IfNeighborManager, IfVxlanManager | CRUD safe | LOW | absent |
| 2.22 | Captive portal | CpZoneManager | CRUD safe | LOW | absent |
| 2.23 | OpenVPN | OvpnInstanceManager, OvpnCsoManager | CRUD safe | LOW | absent |
| 2.24 | DHCP relay | DhcrelayDestManager, DhcrelayRelayManager | CRUD safe | LOW | absent |
| 2.25 | Monit | MonitAlertManager, MonitServiceManager, MonitTestManager | CRUD safe | LOW | absent |
| 2.26 | Dnsmasq | DnsmasqBootManager, DnsmasqDomainManager, DnsmasqHostManager, DnsmasqOptionManager, DnsmasqRangeManager, DnsmasqTagManager | CRUD safe | LOW | absent |

### Phase 2 — Per-Manager Integration Test Scope

> **Rule:** Every manager is tested on the live test zone OPNsense (10.6.239.114).
> All tests use structlog JSON file output for real-time monitoring:
> `tail -f tests/integration/logs/inttest.log | jq .`
>
> Log file: `tests/integration/logs/inttest.log`
> Log config: `conftest.py` → `configure_logging(level="DEBUG", log_file=...)`
> Every test class logs: manager, action, uuid, endpoint, changed, error.

#### Conventions

- **Prefix:** all test objects use `inttest-` (users, groups, rules, aliases)
- **Disabled:** all NAT/filter rules created with `enabled=0` or `disabled=1` — validates CRUD without affecting traffic
- **Cleanup:** every test class has a final cleanup that deletes all `inttest-` objects
- **Error tests:** each manager includes deliberate bad-value tests to capture real API error responses
- **Duplicate detection:** proven on live device that auth rejects duplicates (server-enforced) but FW/IF/TS allow them — AmbiguousMatchError is the only guard (see `test_duplicate_detection.py`)
- **Log link:** integration test runner prints log file path at start — user monitors with `tail -f`

---

#### M01 — AuthUserManager (`auth/user`)

| Endpoint | Method | Action |
|---|---|---|
| `auth/user/search` | GET | list users |
| `auth/user/get/{uuid}` | GET | get user detail |
| `auth/user/add` | POST | create user |
| `auth/user/set/{uuid}` | POST | update user |
| `auth/user/del/{uuid}` | POST | delete user |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create user | `name=inttest-alice, email=alice@example.com, password=T3stP@ss!` | changed=True, action=created | create + no reconfigure (auth immediate) |
| 02 | Idempotent noop | same params | changed=False, action=noop | `_compute_diff` with real API response |
| 03 | Read user | `list(search_phrase=inttest-alice)` | 1 match | search endpoint works |
| 04 | Update email | `email=alice-updated@example.com` | changed=True, action=updated | drift detection |
| 05 | Update idempotent | same updated email | changed=False, action=noop | no false drift |
| 06 | check_mode delete | `check_mode=True` | changed=True but user still exists | dry run safety |
| 07 | Delete user | `state=absent` | changed=True, action=deleted | delete works |
| 08 | Delete idempotent | already gone | changed=False, action=noop | absent noop |
| 09 | **Error: duplicate create** | direct `create()` on existing name | `OpnsenseValidationError` or silent save | real API error |
| 10 | **Error: invalid email** | `email=not-an-email` | capture API response | validation error shape |

**Safety:** `inttest-` prefix only. Never touch `root`, `svc-rune`, or system users.
**Redaction:** password, otp_seed, scrambled_password, authorizedkeys — verify redacted in logs.

---

#### M02 — AuthGroupManager (`auth/group`)

| Endpoint | Method | Action |
|---|---|---|
| `auth/group/search` | GET | list groups |
| `auth/group/get/{uuid}` | GET | get group detail |
| `auth/group/add` | POST | create group |
| `auth/group/set/{uuid}` | POST | update group |
| `auth/group/del/{uuid}` | POST | delete group |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create group | `name=inttest-engineers, description=Test group` | created | CRUD |
| 02 | Idempotent noop | same params | noop | `_compute_diff` |
| 03 | Read group | search by name | 1 match | search |
| 04 | Update description | new description | updated | drift |
| 05 | Delete + idempotent | | deleted then noop | |
| 06 | User-group assignment | assign inttest-alice to inttest-engineers via GID | updated | group_memberships field |
| 07 | Multi-group assignment | inttest-carol to both groups via CSV GIDs | updated | CSV GID format |
| 08 | **Error: delete group with members** | delete group while users assigned | capture API response | error shape |

**Safety:** `inttest-` prefix only. Never touch `admins`, `svc-*` groups.

---

#### M03 — AuthPrivManager (custom, not BaseManager)

| Endpoint | Method | Action |
|---|---|---|
| `auth/user/get/{uuid}` | GET | read user privs |
| `auth/group/get/{uuid}` | GET | read group privs |
| `auth/user/set/{uuid}` | POST | assign/unassign user privs |
| `auth/group/set/{uuid}` | POST | assign/unassign group privs |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Assign priv to group | `priv_id=page-diagnostics-arptable, target_type=group, target_name=inttest-engineers` | created | assignment semantics |
| 02 | Idempotent noop | same | noop | no re-assign |
| 03 | Assign priv to user | `target_type=user, target_name=inttest-alice` | created | user-level priv |
| 04 | check_mode unassign | `state=absent, check_mode=True` | changed but still assigned | dry run |
| 05 | Unassign + idempotent | | deleted then noop | |
| 06 | **Error: invalid target_type** | `target_type=invalid` | ValueError | client-side validation |
| 07 | **Error: nonexistent user** | `target_name=nonexistent-user` | capture error | API error shape |

**Safety:** read-only page privileges only (`page-diagnostics-*`, `page-status-*`). Never assign `page-all` or admin privs.

---

#### M04 — AuthApiKeyManager (custom, not BaseManager)

| Endpoint | Method | Action |
|---|---|---|
| `auth/user/add_api_key/{username}` | POST | generate key |
| `auth/user/search_api_key` | GET | list all keys |
| `auth/user/del_api_key/{id}` | POST | delete key |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create API key | `username=inttest-bob` | key + secret returned | create works |
| 02 | List keys | filter by username | >= 1 key | list works |
| 03 | Create second key | same user | multiple keys per user | no conflict |
| 04 | check_mode delete_all | | changed but keys still exist | dry run |
| 05 | Delete all + idempotent | | deleted then noop | |
| 06 | **Error: key for nonexistent user** | `username=nonexistent-99` | OpnsenseError | API error |

**Safety:** keys for `inttest-*` users only. Never touch `svc-rune` keys.

---

#### M05 — FwAliasManager (`firewall/alias`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/alias/searchItem` | GET | list aliases |
| `firewall/alias/getItem/{uuid}` | GET | get alias detail |
| `firewall/alias/addItem` | POST | create alias |
| `firewall/alias/setItem/{uuid}` | POST | update alias |
| `firewall/alias/delItem/{uuid}` | POST | delete alias |
| `firewall/alias/reconfigure` | POST | apply changes |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create host alias | `name=inttest_alias_host, type=host, content=10.11.1.99` | created | CRUD + reconfigure |
| 02 | Idempotent noop | same params | noop | `_compute_diff` with `type` enum dict |
| 03 | Update content | `content=10.11.1.100` | updated | drift on content |
| 04 | Create network alias | `name=inttest_alias_net, type=network, content=10.11.1.0/24` | created | network type |
| 05 | List contains both | search `inttest` | 2 matches | search works |
| 06 | check_mode delete | | changed but alias exists | dry run |
| 07 | Delete host + network | | deleted then noop | |
| 08 | Create port alias | `name=inttest_alias_port, type=port, content=8080:8090` | created | port range |
| 09 | Port idempotent | same params | noop | |
| 10 | Delete port alias | | deleted | |
| 11 | Create URL alias | `name=inttest_alias_url, type=url, content=https://example.com/blocklist.txt` | created | URL type |
| 12 | URL idempotent | same params | noop | |
| 13 | Delete URL alias | | deleted | |
| 14 | Create URL table alias | `name=inttest_alias_urltbl, type=urltable, content=https://example.com/iplist.txt, updatefreq=1` | created | auto-refresh URL |
| 15 | URL table idempotent | same params | noop | |
| 16 | Delete URL table alias | | deleted | |
| 17 | Create MAC alias | `name=inttest_alias_mac, type=mac, content=00:11:22:33:44:55` | created | MAC type |
| 18 | MAC idempotent | same params | noop | |
| 19 | Delete MAC alias | | deleted | |
| 20 | Verify all cleaned | search `inttest_alias` | 0 matches | no leftovers |
| 21 | **Error: invalid type** | `type=bogus` | capture validation error | API error shape |
| 22 | **Error: invalid content for host** | `type=host, content=not-an-ip` | capture error | validation |

**Safety:** `inttest_alias_` prefix. IPs from test zone subnets (10.11.x.x) only.
**Reconfigure:** yes — alias changes need `firewall/alias/reconfigure`.
**Known noise:** URL/urltable aliases trigger OPNsense system log errors on reconfigure
(`error fetching alias url https://example.com/...`) because the URL doesn't exist.
This is expected — CRUD works correctly, OPNsense just can't resolve the content.
Not a pylib bug. Infra aliases (`inttest_admin_*`) are excluded from cleanup verification.

---

#### M06 — FwFilterManager (`firewall/filter`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/filter/searchRule` | GET | list filter rules |
| `firewall/filter/getRule/{uuid}` | GET | get rule detail |
| `firewall/filter/addRule` | POST | create rule |
| `firewall/filter/setRule/{uuid}` | POST | update rule |
| `firewall/filter/delRule/{uuid}` | POST | delete rule |
| `firewall/filter/apply` | POST | apply changes |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create filter rule (disabled) | `description=inttest-allow-https, action=pass, interface=lan, protocol=TCP, destination_port=443, enabled=0` | created | CRUD + apply, **disabled=safe** |
| 02 | Idempotent noop | same params | noop | `_compute_diff` with `action` + `interface` enum dicts — **key 1.2 fix test** |
| 03 | Update action pass to block | `action=block` | updated | drift on enum field |
| 04 | List contains rule | search `inttest` | 1 match | search |
| 05 | Delete + idempotent | | deleted then noop | |
| 06 | **Error: missing action** | omit `action` | capture validation | required field |
| 07 | **Error: invalid protocol** | `protocol=BOGUS` | capture error | enum validation |

**Safety:** ALL rules created with `enabled=0`. Never enable test rules on live traffic.
**Apply:** yes — filter changes need `firewall/filter/apply`.
**Key test:** noop (02) validates the base.py enum dict fix.

**Floating rules:** No separate API — floating rules are regular filter rules with
`direction=any` + multi-interface (CSV). The `interface` field is multi-select.
`quick=1` evaluates and stops, `quick=0` continues to per-interface rules.
No `floating` field in the schema — the combination defines it.

**Phase 3 floating rule test case:** When VLAN sub-interfaces exist:
```
description=inttest-float-block-dmz-to-svc
action=block, direction=any, interface=vlan1320,vlan1330
source_net=10.11.2.0/24, destination_net=10.11.3.0/24
quick=1, enabled=0
```
Validates: multi-interface select, floating rule semantics, inter-zone blocking.
**Key test:** noop (02) validates the base.py enum dict fix.

---

#### M07 — FwDnatManager (`firewall/d_nat`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/d_nat/searchRule` | GET | list DNAT rules |
| `firewall/d_nat/getRule/{uuid}` | GET | get rule detail |
| `firewall/d_nat/addRule` | POST | create rule |
| `firewall/d_nat/setRule/{uuid}` | POST | update rule |
| `firewall/d_nat/delRule/{uuid}` | POST | delete rule |
| `firewall/d_nat/apply` | POST | apply changes |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create DNAT rule (disabled) | `descr=inttest-dnat-http, interface=wan, target=10.11.2.10, local-port=80, disabled=1` | created | **disabled=1 — no pf reload risk** |
| 02 | Idempotent noop | same params | noop | `_compute_diff` with `interface`, `ipprotocol`, `protocol` enum dicts |
| 03 | Update target | `target=10.11.2.11` | updated | drift |
| 04 | Delete + idempotent | | deleted then noop | |
| 05 | **Error: invalid target IP** | `target=not-an-ip` | capture error | validation |

**Safety:** ALL DNAT rules created with `disabled=1`. D-NAT apply on WAN crashed FW on 2026-04-05. Disabled rules are safe — apply runs but pf does not load the rule.
**Phase 3 only:** enable DNAT rule for E2E test (3.2) when LXC webdmz exists.

---

#### M08 — FwSourceNatManager (`firewall/source_nat`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/source_nat/searchRule` | GET | list SNAT rules |
| `firewall/source_nat/getRule/{uuid}` | GET | get rule detail |
| `firewall/source_nat/addRule` | POST | create rule |
| `firewall/source_nat/setRule/{uuid}` | POST | update rule |
| `firewall/source_nat/delRule/{uuid}` | POST | delete rule |
| `firewall/source_nat/apply` | POST | apply changes |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create SNAT rule (disabled) | `description=inttest-snat, interface=wan, source_net=10.11.3.0/24, target=wanip, enabled=0` | created | **enabled=0 — safe** |
| 02 | Idempotent noop | same params | noop | `_compute_diff` enum dicts |
| 03 | Delete + idempotent | | deleted then noop | |
| 04 | **Error: invalid source_net** | `source_net=bogus` | capture error | validation |

**Safety:** same as DNAT — `enabled=0` always. Never enable SNAT on test zone without sandbox.

---

#### M09 — FwCategoryManager (`firewall/category`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/category/searchItem` | GET | list |
| `firewall/category/getItem/{uuid}` | GET | get |
| `firewall/category/addItem` | POST | create |
| `firewall/category/setItem/{uuid}` | POST | update |
| `firewall/category/delItem/{uuid}` | POST | delete |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create category | `name=inttest-cat` | created | no apply needed |
| 02 | Idempotent noop | same | noop | |
| 03 | Update + delete | | | |
| 04 | **Error: duplicate name** | create same name twice | capture error | |

**Safety:** `inttest-` prefix. No apply endpoint — changes immediate.

---

#### M10 — FwGroupManager (`firewall/group`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/group/searchItem` | GET | list |
| `firewall/group/getItem/{uuid}` | GET | get |
| `firewall/group/addItem` | POST | create |
| `firewall/group/setItem/{uuid}` | POST | update |
| `firewall/group/delItem/{uuid}` | POST | delete |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create interface group | `ifname=inttest_grp, members=lan, descr=...` | created | no apply needed |
| 02 | Idempotent noop | same | noop | |
| 03 | Update description | new descr | updated | drift |
| 04 | Delete + idempotent | | deleted then noop | |
| 05 | **Error: invalid ifname** | special chars | capture error | |

**Safety:** `inttest_` prefix. `_match_key=ifname`. No apply endpoint.
**Required field:** `members` is mandatory — OPNsense rejects empty groups.
**Phase 3 use case:** When VLAN sub-interfaces exist (vlan1310/vlan1320/vlan1330),
create `inttest_internal` with `members=vlan1310,vlan1330` (MGMT+SVC) and use it
in a single filter rule to block DMZ access from both zones.

---

#### M11 — FwOneToOneManager (`firewall/one_to_one`)

| Endpoint | Method | Action |
|---|---|---|
| `firewall/one_to_one/searchRule` | GET | list |
| `firewall/one_to_one/getRule/{uuid}` | GET | get |
| `firewall/one_to_one/addRule` | POST | create |
| `firewall/one_to_one/setRule/{uuid}` | POST | update |
| `firewall/one_to_one/delRule/{uuid}` | POST | delete |
| `firewall/one_to_one/apply` | POST | apply |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create 1:1 NAT (disabled) | `description=inttest-1to1, disabled=1, interface=wan, source=10.11.2.10, destination=any, external=10.6.239.200` | created | **disabled=1** |
| 02 | Idempotent noop | same | noop | `_compute_diff` enum dicts |
| 03 | Delete + idempotent | | | |
| 04 | **Error: invalid source** | `source=bogus` | capture error | |

**Safety:** `disabled=1` always. Same NAT safety rules as DNAT/SNAT.

---

#### M12 — TsPipeManager (`trafficshaper/settings`)

| Endpoint | Method | Action |
|---|---|---|
| `trafficshaper/settings/searchPipes` | GET | list (custom override) |
| `trafficshaper/settings/getPipe/{uuid}` | GET | get |
| `trafficshaper/settings/addPipe` | POST | create |
| `trafficshaper/settings/setPipe/{uuid}` | POST | update |
| `trafficshaper/settings/delPipe/{uuid}` | POST | delete |
| `trafficshaper/service/reconfigure` | POST | apply |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create pipe | `description=inttest-pipe, bandwidth=10, bandwidthMetric=Mbit` | created | custom search endpoint |
| 02 | Idempotent noop | same | noop | |
| 03 | Update bandwidth | `bandwidth=20` | updated | |
| 04 | Delete + idempotent | | | |
| 05 | **Error: invalid bandwidth** | `bandwidth=-1` | capture error | |

**Safety:** `inttest-` prefix. Pipes don't affect traffic until linked to queues/rules.

---

#### M13 — IfVlanManager (`interfaces/vlan_settings`) — in stash

| Endpoint | Method | Action |
|---|---|---|
| `interfaces/vlan_settings/searchItem` | GET | list |
| `interfaces/vlan_settings/getItem/{uuid}` | GET | get |
| `interfaces/vlan_settings/addItem` | POST | create |
| `interfaces/vlan_settings/setItem/{uuid}` | POST | update |
| `interfaces/vlan_settings/delItem/{uuid}` | POST | delete |
| `interfaces/vlan_settings/reconfigure` | POST | apply |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create test VLAN | `descr=inttest-vlan, tag=1399, if=vtnet0` | created | VLAN CRUD |
| 02 | Idempotent noop | same | noop | `_compute_diff` |
| 03 | Update description | new descr | updated | |
| 04 | Delete + idempotent | | | |
| 05 | **Error: duplicate VLAN tag** | `tag=1310` (existing) | capture error | |
| 06 | **Error: invalid tag** | `tag=99999` | capture error | |

**Safety:** `inttest-` prefix. Use tag=1399 (unused). **DO NOT touch VLANs 1310/1320/1330** — test zone infra.

---

#### M14 — IfVipManager (`interfaces/vip_settings`) — in stash

| Endpoint | Method | Action |
|---|---|---|
| `interfaces/vip_settings/searchItem` | GET | list |
| `interfaces/vip_settings/getItem/{uuid}` | GET | get |
| `interfaces/vip_settings/addItem` | POST | create |
| `interfaces/vip_settings/setItem/{uuid}` | POST | update |
| `interfaces/vip_settings/delItem/{uuid}` | POST | delete |
| `interfaces/vip_settings/reconfigure` | POST | apply |

| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create VIP (ipalias) | `descr=inttest-vip, address=10.11.1.200, mode=ipalias, interface=lan` | created | VIP CRUD |
| 02 | Idempotent noop | same | noop | `_compute_diff` with `mode` enum dict |
| 03 | Delete + idempotent | | | |
| 04 | **Error: invalid address** | `address=bogus` | capture error | |
| 05 | **Error: duplicate address** | same IP on same interface | capture error | |

**Safety:** `inttest-` prefix. Use 10.11.1.200 (test MGMT subnet, unused).
**Redaction:** `password` field (CARP) — verify redacted in logs.

---

#### Cross-cutting: Error Handling (once, shared across all managers)

| # | Use case | Expected | File |
|---|---|---|---|
| E01 | Invalid API credentials | `OpnsenseAuthError`, status_code=401 | `test_error_handling.py` |
| E02 | Nonexistent endpoint | `OpnsenseEndpointMissingError`, status_code=404 | |
| E03 | Invalid state (`ensure(state="bogus")`) | `ValueError` | |
| E04 | Extremely short timeout (0.001s) | `OpnsenseTimeoutError` or `OpnsenseConnectionError` | |
| E05 | Unreachable host (192.0.2.1) | `OpnsenseConnectionError` | |
| E06 | All exception attributes accessible | `message`, `status_code`, `endpoint` | |

---

#### Real-Time Log Monitoring

All integration tests write to: `tests/integration/logs/inttest.log`

**Monitor from Rune VM:**
```bash
tail -f tests/integration/logs/inttest.log | jq .
```

**Log format per event (JSON):**
```json
{
  "ts": "2026-04-07T18:00:00Z",
  "level": "info",
  "logger": "opnsense.managers.base",
  "msg": "created auth/user inttest-alice uuid=abc-123",
  "action": "created",
  "changed": true,
  "uuid": "abc-123",
  "match_field": "name",
  "match_value": "inttest-alice",
  "endpoint": "auth/user"
}
```

**Severity convention:**

| Level | When |
|---|---|
| DEBUG | noop — no change needed |
| INFO | create, update |
| WARNING | delete |
| ERROR | mutation failed (logged then re-raised) |
| CRITICAL | auth failure |

---

### Phase 3 — E2E Playbook (pylib first, then Ansible)

> **Goal:** Build the test zone infra programmatically via pylib, then validate
> traffic flows across WAN/LAN zones (MGMT, DMZ, SVC). Rune VM monitors.

#### 3.0 — Pylib Provisioning Script

Build the test zone from scratch using lib-opnsense managers:

| Step | Manager | Action | Params |
|---|---|---|---|
| 1 | IfVlanManager | Create VLAN 1310 sub-if | `tag=1310, if=vtnet0, descr=test-mgmt` |
| 2 | IfVlanManager | Create VLAN 1320 sub-if | `tag=1320, if=vtnet0, descr=test-dmz` |
| 3 | IfVlanManager | Create VLAN 1330 sub-if | `tag=1330, if=vtnet0, descr=test-svc` |
| 4 | FwAliasManager | Create admin hosts alias | `name=inttest_admin_hosts, type=host, content=10.100.0.101` |
| 5 | FwAliasManager | Create DMZ server alias | `name=inttest_dmz_servers, type=host, content=10.11.2.10` |
| 6 | FwAliasManager | Create SVC server alias | `name=inttest_svc_servers, type=host, content=10.11.3.10` |
| 7 | FwFilterManager | WAN allow admin SSH+HTTPS (disabled) | `interface=wan, source=inttest_admin_hosts, destination_port=22,443, enabled=0` |
| 8 | FwFilterManager | LAN-DMZ allow HTTP from anywhere (disabled) | `interface=vlan1320, action=pass, destination_port=80, enabled=0` |
| 9 | FwFilterManager | LAN-SVC allow HTTP from DMZ only (disabled) | `interface=vlan1330, source=inttest_dmz_servers, destination_port=80, enabled=0` |
| 10 | FwFilterManager | LAN-SVC block all other (disabled) | `interface=vlan1330, action=block, enabled=0` |
| 11 | FwDnatManager | WAN:8080 to webdmz:80 (disabled) | `interface=wan, target=10.11.2.10, local-port=80, disabled=1` |

All rules created **disabled**. Phase 3 E2E enables them one by one and validates.

#### 3.1 — E2E: Enable + Validate per zone

| # | Test | Enable rule | Validate from Rune | Validate from OPNsense SSH |
|---|---|---|---|---|
| 3.1.1 | WAN admin access | rule 7 enabled=1 | `curl -k https://10.6.239.114` 200 | — |
| 3.1.2 | DNAT to DMZ | rule 11 disabled=0 | `curl http://10.6.239.114:8080` whoami response | — |
| 3.1.3 | DMZ HTTP | rule 8 enabled=1 | — | `curl http://10.11.2.10:80` whoami |
| 3.1.4 | SVC from DMZ only | rule 9 enabled=1 | — | `ssh root@opn "curl http://10.11.3.10:80"` whoami |
| 3.1.5 | SVC blocked from WAN | rule 10 enabled=1 | `curl http://10.11.3.10:80` timeout | — |

**Depends on:** LXC webdmz (0.9) + LXC websrv (0.10) running `traefik/whoami`.

#### 3.2 — Additional E2E tests (when managers exist)

| # | Test | What it validates | Depends on |
|---|---|---|---|
| 3.2.1 | DNS override websrv.test nslookup | DNS | 2.11 |
| 3.2.2 | Kea subnet + reservation DHCP lease | DHCP | 2.12 |
| 3.2.3 | WireGuard peer tunnel up | VPN | 2.14 |

#### 3.3 — Rune VM Monitor Script

Continuous health check running on Rune (10.100.0.101):

```python
# tests/e2e/monitor.py — runs in loop, logs to JSON
checks = [
    ("API reachable",    "GET",  "https://10.6.239.114/api/core/firmware/status"),
    ("SSH reachable",    "ssh",  "root@10.6.239.114 echo ok"),
    ("DNAT webdmz",     "curl", "http://10.6.239.114:8080"),
    ("DMZ direct",       "ssh",  "root@10.6.239.114 curl -s http://10.11.2.10:80"),
    ("SVC direct",       "ssh",  "root@10.6.239.114 curl -s http://10.11.3.10:80"),
    ("SVC blocked WAN",  "curl", "http://10.11.3.10:80 --connect-timeout 3"),  # expect fail
]
# Log: {ts, check, result, latency_ms, status: pass|fail}
# File: tests/e2e/logs/monitor.log
```

**Monitor from terminal:**
```bash
tail -f tests/e2e/logs/monitor.log | jq .
```

### Phase 4 — OpenAPI + Ansible (Rune)

| # | Task | Depends on |
|---|---|---|
| 4.1 | Generate OpenAPI spec (`openapi/opnsense.yaml`) | Phase 2 complete |
| 4.2 | Ansible modules wrapping lib-opnsense | Phase 2 complete |
| 4.3 | Ansible roles per concern | 4.2 |
| 4.4 | Ansible E2E playbooks | 4.3 |

---

## OPNsense Setup Checklist

User prepares manually:

- [x] Install OPNsense from ISO (console)
- [x] Enable WebGUI (HTTPS on LAN)
- [x] `pfctl -d` from console (disable firewall for initial API access)
- [x] Create user `svc-rune` with admin group
- [x] Generate API key for `svc-rune` → store in `infra/secrets/`
- [x] Set `svc-rune` shell = `/bin/sh` (WebGUI or API — default is "none" which kills SSH)
- [x] Add SSH pubkey(s) to `svc-rune` authorizedkeys (WebGUI or API, newline-separated for multiple)
- [x] Enable SSH (System → Administration → Secure Shell)
- [x] Enable root login (permit root SSH) — **KEEP for bootstrap + OOB emergency**
- [ ] Disable root SSH — **AFTER** VPN + monitoring validated (Phase 3), Proxmox console remains OOB fallback
- [x] Upgrade to 26.1.5
- [x] Rune verifies: API works (`GET /api/core/firmware/status`)
- [x] Rune verifies: SSH works (`ssh -i ~/.ssh/id_ed25519_opnsense root@10.6.239.114`)

### Access Notes

**SSH:**
- Key: `~/.ssh/id_ed25519_opnsense` (no passphrase, test zone only)
- User: `root` only (non-root gets "Connection closed")
- WebGUI "Authorized keys" field does NOT sync to `/root/.ssh/authorized_keys` — known bug ([GitHub #8221](https://github.com/opnsense/core/issues/8221))
- Must add key to filesystem manually from console + add in WebGUI (survives config reload)

**API:**
- User: `svc-rune` (admin group)
- Token: `infra/secrets/OPNsense.internal_root_apikey.txt`

**Firewall (WAN on private network):**
- WAN is on private 10.6.224.0/20 — NOT a public IP
- **MUST** uncheck "Block private networks" + "Block bogon networks" on WAN interface (Interfaces → WAN → Generic configuration)
- Without this: WAN blocks all traffic from 10.0.0.0/8 before any allow rule is evaluated (quick rule)
- WAN allow rule created via API: `inttest_admin_hosts` (10.100.0.101 + 10.6.239.113) → SSH + HTTPS
- **pf is ENABLED** — `pfctl -d` is no longer needed
- Confirmed: `pfctl -e` + API OK + SSH OK

**Test zone specific (private WAN, same-subnet clients):**
- MVC filter rules auto-add `reply-to (gateway)` — designed for multi-WAN with public IPs
- On test zone: WAN is private 10.6.224.0/20, admin clients are same L2 subnet
- `reply-to` sends replies via gateway instead of direct L2 → breaks same-subnet access
- Fix: set `disablereplyto=1` on WAN allow rules (Firewall → Rules → edit → Advanced → "Disable reply-to")
- For production with public WAN: keep `reply-to` enabled — it's correct

**WAN IP:**
- Currently DHCP: 10.6.239.114
- Will be set to static 10.6.239.114/20 (task 0.8)

## Bill of Materials — Full Test Infrastructure

### Virtual Machines

| # | VM | VMID | Role | OS | Network |
|---|---|---|---|---|---|
| 1 | OPNsense test | 101 | Firewall under test | OPNsense 26.1.5 | WAN: vmbrWAN3 (10.6.239.114), LAN: vmbrAPPS (trunk) |
| 2 | Rune VM | — | Test client + API caller | Linux | WAN: 10.100.0.101 |
| 3 | Win11 Desktop | — | VPN client (WireGuard, OpenVPN) | Windows 11 | WAN: 10.100.0.x |

### LXC Containers

| # | LXC | IP (v4) | IP (v6) | VLAN | Zone | Purpose | Used by scopes |
|---|---|---|---|---|---|---|---|
| 1 | lxc-webdmz-test-01 | 10.11.2.10 (static) | fd11:2::10 (static) | 1320 | DMZ | DNAT target, HTTP server | firewall, dns, interfaces |
| 2 | lxc-websrv-test-01 | 10.11.3.10 (static) | fd11:3::10 (static) | 1330 | SVC | Internal service, inter-zone routing | firewall, routing, shaper |
| 3 | lxc-dhcpclient-test-01 | DHCP (Kea4) | DHCPv6 (Kea6) | 1320 | DMZ | DHCP lease validation | dhcp |

### VLANs

| # | VLAN ID | VNet | Subnet (v4) | Subnet (v6) | Gateway | Purpose |
|---|---|---|---|---|---|---|
| 1 | 1310 | tmgmt | 10.11.1.0/24 | fd11:1::/64 | 10.11.1.1 / fd11:1::1 | Management (API, SSH) |
| 2 | 1320 | tdmz | 10.11.2.0/24 | fd11:2::/64 | 10.11.2.1 / fd11:2::1 | DMZ (public-facing via DNAT) |
| 3 | 1330 | tsvc | 10.11.3.0/24 | fd11:3::/64 | 10.11.3.1 / fd11:3::1 | Services (internal only) |
| 4 | 1340 | tvpn | 10.11.4.0/24 | fd11:4::/64 | 10.11.4.1 / fd11:4::1 | VPN clients (optional isolation) |

### VPN Tunnels

| # | Protocol | Interface | Subnet | Port | Purpose |
|---|---|---|---|---|---|
| 1 | WireGuard | wg0 | 10.10.0.0/24 | 51820 | Remote access (Win11/mobile) |
| 2 | OpenVPN | tun0 | 10.10.1.0/24 | 1194 | Legacy remote access |
| 3 | IPsec | ipsec0 | 10.10.2.0/24 | 500/4500 | Site-to-site (test) |

### Scope → Infrastructure Matrix

| Scope | OPNsense | webdmz LXC | websrv LXC | dhcpclient LXC | Rune VM | Win11 | VPN tunnel |
|---|---|---|---|---|---|---|---|
| auth | x | | | | x | | |
| firewall | x | x (DNAT) | x (inter-zone) | | x (WAN) | | |
| interfaces | x | | | | | | |
| routing | x | | x (route target) | | | | |
| dns | x | | | | x (nslookup) | | |
| dhcp | x | | | x (lease) | | | |
| vpn | x | | | | x (IPsec) | x (WG/OVPN) | x |
| shaper | x | | x (iperf3) | | | | |
| trust | x | | | | | | |
| services | x | | | | | | |

### Total Infrastructure Count

| Resource | Count |
|---|---|
| VMs | 3 (OPNsense + Rune + Win11) |
| LXCs | 3 (webdmz + websrv + dhcpclient) |
| VLANs | 4 (MGMT + DMZ + SVC + VPN) |
| VPN tunnels | 3 (WG + OVPN + IPsec) |
| Subnets (v4) | 7 (3 zones + 1 VPN zone + 3 tunnels) |
| Subnets (v6) | 4 (3 zones + 1 VPN zone, ULA fd11:x::/64) |

## Deliverables

| Deliverable | Location |
|---|---|
| lib-opnsense 100% CRUD managers | `src/opnsense/managers/` |
| Scope + use case doc per domain | `docs/managers/{domain}.md` |
| Unit tests per manager | `tests/unit/` |
| Integration tests (live device) | `tests/integration/` |
| OpenAPI spec (swagger) | `openapi/opnsense.yaml` |
| Updated api-coverage.md (status per stage) | `docs/api-coverage.md` |
| Updated api/gaps.md | `docs/api/gaps.md` |
