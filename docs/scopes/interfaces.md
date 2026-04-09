<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-systems/lib-opnsense
-->

# Interfaces Scope — lib-opnsense

## Overview
9 managers: IfVlanManager, IfVipManager, IfBridgeManager, IfGifManager, IfGreManager, IfLaggManager, IfLoopbackManager, IfNeighborManager, IfVxlanManager.
All require reconfigure after CRUD.

## Network Diagram
```
  OPNsense (10.6.239.114)
  │
  ├── vtnet0 (LAN) ── vmbrAPPS trunk
  │   ├── vlan1310 → 10.11.1.1/24 (MGMT)
  │   ├── vlan1320 → 10.11.2.1/24 (DMZ)
  │   └── vlan1330 → 10.11.3.1/24 (SVC)
  │
  ├── vtnet1 (WAN) ── vmbrWAN3
  │   └── 10.6.239.114/20
  │
  └── VIPs, bridges, tunnels (GIF/GRE/VXLAN)
      created via API for testing
```

## Managers

### IfVlanManager (interfaces/vlan_settings)
- Match key: tag + if (composite)
- Apply: interfaces/vlan_settings/reconfigure
- Module: `opnsense.managers.interfaces.vlan`

### IfVipManager (interfaces/vip_settings)
- Match key: description
- Apply: interfaces/vip_settings/reconfigure
- CARP fields: vhid, advbase, advskew, password
- Redact: password
- Module: `opnsense.managers.interfaces.vip`

### IfBridgeManager through IfVxlanManager
- Each has standard CRUD with reconfigure
- Match key: description (most) or name
- Modules: `opnsense.managers.interfaces.{bridge,gif,gre,lagg,loopback,neighbor,vxlan}`

## Use Cases

### IfVlanManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create VLAN | tag=1399, if=vtnet0, descr=inttest-vlan | created | VLAN CRUD |
| 02 | Idempotent noop | same | noop | composite match |
| 03 | Delete + idempotent | | deleted then noop | |
| 04 | Error: invalid tag | tag=99999 | validation error | |

### IfVipManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create VIP (ipalias) | descr=inttest-vip, address=10.11.1.200, mode=ipalias | created | |
| 02 | Idempotent noop | same | noop | mode enum dict |
| 03 | Delete | | deleted | |
| 04 | Error: invalid address | address=bogus | validation error | |

### IfBridgeManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create bridge | description=inttest-bridge | created | |
| 02 | Delete | | deleted | |

### IfGifManager, IfGreManager, IfVxlanManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create tunnel | description=inttest-{type} | created | tunnel CRUD |
| 02 | Delete | | deleted | |

### IfLaggManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create LAGG | description=inttest-lagg | created | |
| 02 | Delete | | deleted | |

### IfLoopbackManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create loopback | description=inttest-lo | created | |
| 02 | Delete | | deleted | |

### IfNeighborManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create neighbor | description=inttest-neighbor | created | NDP/ARP |
| 02 | Delete | | deleted | |

## Bill of Materials
- OPNsense test device: 10.6.239.114
- VLANs 1310/1320/1330 already configured (test zone)
- Test VLAN tag: 1399 (unused, safe for create/delete)
- Test VIP address: 10.11.1.200 (unused in MGMT subnet)

## Safety Boundaries
- NEVER modify existing VLANs 1310/1320/1330 (test zone infra)
- Use tag 1399+ for test VLANs
- inttest- prefix on all descriptions
- VIP test addresses from test subnets only

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 9 managers |
| Integration tests | PASS | Full lifecycle |
