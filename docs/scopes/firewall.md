<!--
Copyright BY-SYSTEMS SRL
SPDX-License-Identifier: MIT
https://github.com/by-systems/lib-opnsense
-->

# Firewall Scope — lib-opnsense

## Diagrams

- [Network Diagram](../../assets/diagrams/scope-firewall-nwdiag.puml)
- [FW Rule State Diagram](../../assets/diagrams/scope-firewall-state.puml)
- [Class Diagram — core architecture](../../assets/diagrams/scope-lib-class.puml)

## Overview
8 managers: FwAliasManager, FwFilterManager, FwDnatManager, FwSourceNatManager, FwOneToOneManager, FwNptManager, FwCategoryManager, FwGroupManager.
All require reconfigure/apply after CRUD. ALL test rules created DISABLED (enabled=0 or disabled=1).
FW rules allow duplicates — AmbiguousMatchError is the only guard.
All FW managers support sequence field for rule ordering.

## Network Diagram

```
  Rune VM (10.100.0.101)
       │
       │ WAN (10.6.224.0/20)
       ▼
  ┌──────────────────────────────────┐
  │       OPNsense (10.6.239.114)    │
  │                                  │
  │  FW Filter: WAN/LAN/VLAN rules  │
  │  D-NAT: WAN:port → DMZ LXC     │
  │  S-NAT: LAN→WAN masquerade     │
  │  1:1 NAT: IP mapping           │
  │  NPTv6: IPv6 prefix translation │
  │                                  │
  │  VLAN 1310 ─ MGMT (10.11.1.0/24)│
  │  VLAN 1320 ─ DMZ  (10.11.2.0/24)│
  │  VLAN 1330 ─ SVC  (10.11.3.0/24)│
  └──┬──────────┬──────────┬─────────┘
     │          │          │
   MGMT       DMZ        SVC
            10.11.2.10  10.11.3.10
            (webdmz)    (websrv)
```

## Managers

### FwAliasManager (firewall/alias)
- Endpoint: firewall/alias, suffix: Item
- Match key: name (unique, server-enforced)
- Apply: firewall/alias/reconfigure
- Types: host, network, port, url, urltable, mac
- Module: `opnsense.managers.firewall.alias`

### FwFilterManager (firewall/filter)
- Endpoint: firewall/filter, suffix: Rule
- Match key: description (NOT unique — AmbiguousMatchError)
- Apply: firewall/filter/apply
- Fields: action, interface, direction, protocol, source_net, destination_net, destination_port, source_not, destination_not, gateway, categories, statetype, sequence, enabled
- Module: `opnsense.managers.firewall.filter`

### FwDnatManager (firewall/d_nat)
- Endpoint: firewall/d_nat, suffix: Rule
- Match key: descr (NOT unique)
- Apply: firewall/d_nat/apply
- Nested dict: source, destination
- SAFETY: D-NAT apply on WAN crashed FW on 2026-04-05. Always disabled=1.
- Module: `opnsense.managers.firewall.dnat`

### FwSourceNatManager (firewall/source_nat)
- Endpoint: firewall/source_nat, suffix: Rule
- Match key: description (NOT unique)
- Apply: firewall/source_nat/apply
- Module: `opnsense.managers.firewall.source_nat`

### FwOneToOneManager (firewall/one_to_one)
- Endpoint: firewall/one_to_one, suffix: Rule
- Match key: description (NOT unique)
- Apply: firewall/one_to_one/apply
- Module: `opnsense.managers.firewall.one_to_one`

### FwNptManager (firewall/npt)
- Endpoint: firewall/npt, suffix: Rule
- Match key: description (NOT unique)
- Apply: firewall/npt/apply
- IPv6 prefix translation (NPTv6)
- Module: `opnsense.managers.firewall.npt`

### FwCategoryManager (firewall/category)
- Endpoint: firewall/category, suffix: Item
- Match key: name
- No reconfigure needed
- Module: `opnsense.managers.firewall.category`

### FwGroupManager (firewall/group)
- Endpoint: firewall/group, suffix: Item (search: searchItem)
- Match key: name
- Module: `opnsense.managers.firewall.group`

## Use Cases

### FwAliasManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create host alias | name=inttest_alias_host, type=host, content=10.11.1.99 | created | CRUD + reconfigure |
| 02 | Idempotent noop | same | noop | diff with enum dict |
| 03 | Update content | content=10.11.1.100 | updated | drift |
| 04 | Create network alias | type=network, content=10.11.1.0/24 | created | network type |
| 05 | Create port alias | type=port, content=8080:8090 | created | port range |
| 06 | Create URL alias | type=url | created | URL type |
| 07 | Create URL table | type=urltable, updatefreq=1 | created | auto-refresh |
| 08 | Create MAC alias | type=mac, content=00:11:22:33:44:55 | created | MAC |
| 09 | Delete all + verify | search inttest_alias | 0 matches | cleanup |
| 10 | Error: invalid type | type=bogus | validation error | |
| 11 | Error: invalid content | type=host, content=not-an-ip | validation error | |

### FwFilterManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create rule (disabled) | description=inttest-allow-https, action=pass, interface=lan, protocol=TCP, destination_port=443, enabled=0 | created | CRUD + apply |
| 02 | Idempotent noop | same | noop | enum dict fix |
| 03 | Update action | action=block | updated | drift on enum |
| 04 | Sequence field | sequence=10 | updated | rule ordering |
| 05 | Delete + idempotent | | deleted then noop | |
| 06 | Error: missing action | omit action | validation error | |
| 07 | Error: invalid protocol | protocol=BOGUS | validation error | |
| 08 | **Inverted source** | source_not=1, source_net=10.11.2.0/24 (NOT DMZ), enabled=0 | created | source inversion |
| 09 | **Inverted destination** | destination_not=1, destination_net=10.11.3.0/24, enabled=0 | created | destination inversion |
| 10 | **Sequence ordering** | create 3 rules with sequence=10,20,30, verify list order | ordered by sequence | rule evaluation order |
| 11 | **Disable/enable toggle** | create enabled=0, update enabled=1, verify, update back to enabled=0 | changed each time | toggle without traffic risk |
| 12 | **Duplicate: same description** | create rule with same description | AmbiguousMatchError on next ensure() | lib-side guard (API allows it) |
| 13 | **Categories field** | categories=inttest-cat (from FwCategoryManager) | created with category link | cross-manager reference |
| 14 | **Gateway field** | gateway=Null4, enabled=0 | created | policy routing (blackhole safe) |
| 15 | **Port: valid single** | destination_port=443 | created | port accepted |
| 16 | **Port: valid range** | destination_port=80:443 | created | range accepted |
| 17 | **Port: valid comma** | destination_port=80,443,8080 | created | multi-port accepted |
| 18 | **Port: alias name** | destination_port=inttest_web_ports (alias) | created | alias reference accepted |
| 19 | **Port: boundary min** | destination_port=1 | created | min port |
| 20 | **Port: boundary max** | destination_port=65535 | created | max port |
| 21 | **Error: port 0** | destination_port=0 | API rejection | below range |
| 22 | **Error: port > 65535** | destination_port=125657 | API rejection | above range |
| 23 | **Error: negative port** | destination_port=-1 | API rejection | invalid |

> **Port fields note:** `source_port` and `destination_port` are typed as `str` in the
> lib to match the OPNsense MVC model exactly. The API validates server-side.
> See [port-field-reference.md](../port-field-reference.md) for the full inventory.

### FwDnatManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create DNAT (disabled) | descr=inttest-dnat-http, interface=wan, target=10.11.2.10, local-port=80, disabled=1 | created | disabled=safe |
| 02 | Idempotent noop | same | noop | nested dict diff |
| 03 | Update target | target=10.11.2.11 | updated | drift |
| 04 | Delete + idempotent | | deleted then noop | |
| 05 | Error: invalid target | target=not-an-ip | validation error | |
| 06 | **Duplicate: same description** | create second DNAT with same descr | AmbiguousMatchError | lib detects duplicates |

### FwSourceNatManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create SNAT (disabled) | description=inttest-snat, interface=wan, source_net=10.11.3.0/24, target=wanip, enabled=0 | created | safe |
| 02 | Idempotent noop | same | noop | enum dicts |
| 03 | Delete + idempotent | | deleted then noop | |
| 04 | **Duplicate: same description** | create second SNAT same description | AmbiguousMatchError | |

### FwOneToOneManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create 1:1 NAT (disabled) | description=inttest-1to1, interface=wan, enabled=0 | created | |
| 02 | Idempotent + delete | | noop then deleted | |

### FwNptManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create NPTv6 (disabled) | description=inttest-npt, enabled=0 | created | IPv6 prefix translation |
| 02 | Idempotent + delete | | noop then deleted | |

### FwCategoryManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create category | name=inttest-cat | created | no reconfigure |
| 02 | Idempotent + delete | | noop then deleted | |

### FwGroupManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create group | name=inttest-fwgrp | created | |
| 02 | Idempotent + delete | | noop then deleted | |

## Bill of Materials
- OPNsense test device: 10.6.239.114
- For D-NAT E2E: lxc-webdmz-test-01 (10.11.2.10) on VLAN 1320
- For inter-zone rules: lxc-websrv-test-01 (10.11.3.10) on VLAN 1330
- DNAT E2E validation: curl from Rune VM (WAN side)

## Safety Boundaries
- ALL rules created with enabled=0 or disabled=1
- NEVER enable NAT rules on live WAN (D-NAT apply crashed FW on 2026-04-05)
- inttest- or inttest_ prefix on all objects
- IPs from test zone subnets only (10.11.x.x)
- Phase 3 only: enable rules for E2E with LXC targets
- sequence field validates rule ordering without affecting traffic

## Logging

Logger path follows package structure:
```
opnsense.managers.firewall.alias       → FwAliasManager
opnsense.managers.firewall.filter      → FwFilterManager
opnsense.managers.firewall.dnat        → FwDnatManager
opnsense.managers.firewall.source_nat  → FwSourceNatManager
opnsense.managers.firewall.one_to_one  → FwOneToOneManager
opnsense.managers.firewall.npt         → FwNptManager
opnsense.managers.firewall.category    → FwCategoryManager
opnsense.managers.firewall.group       → FwGroupManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.firewall"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 8 managers |
| Integration tests | PASS | Full lifecycle, all disabled |
