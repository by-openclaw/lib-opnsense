<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# DHCP Scope — lib-opnsense

## Overview
5 managers: Kea4SubnetManager, Kea4ReservationManager, Kea4PeerManager, Kea6SubnetManager, Kea6ReservationManager.
Kea DHCPv4 + DHCPv6 on OPNsense 26.1 (replaces ISC DHCP). Reservations need parent subnet UUID.
Kea6 subnet needs interface field. option_data uses nested dict validator.

## Network Diagram
```
  OPNsense Kea DHCP
  │
  ├── DHCPv4 on LAN (vlan1310/1320/1330)
  │   └── Subnet 10.11.2.0/24
  │       └── Reservation: MAC → 10.11.2.20
  │
  ├── DHCPv6 on LAN
  │   └── Subnet fd11:2::/64
  │       └── Reservation: DUID → fd11:2::20
  │
  └── lxc-dhcpclient-test-01 (DHCP client)
      Validates actual lease assignment
```

## Managers
- Kea4SubnetManager: kea/dhcpv4, suffix Subnet. Match: subnet. Module: `opnsense.managers.dhcp.kea4_subnet`
- Kea4ReservationManager: kea/dhcpv4, suffix Reservation. Match: ip_address. Needs parent subnet UUID. Module: `opnsense.managers.dhcp.kea4_reservation`
- Kea4PeerManager: kea/dhcpv4, suffix Peer. Match: name. Module: `opnsense.managers.dhcp.kea4_peer`
- Kea6SubnetManager: kea/dhcpv6, suffix Subnet6. Match: subnet. Needs interface field. Module: `opnsense.managers.dhcp.kea6_subnet`
- Kea6ReservationManager: kea/dhcpv6, suffix Reservation6. Match: ip_address. Module: `opnsense.managers.dhcp.kea6_reservation`

## Use Cases

### Kea4SubnetManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create subnet | subnet=10.11.2.0/24, pools=10.11.2.100-10.11.2.200 | created | |
| 02 | Idempotent + delete | | noop then deleted | |
| 03 | With option_data | option_data nested dict | created | nested dict validator |

### Kea4ReservationManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create reservation | subnet=<uuid>, hw_address=..., ip_address=10.11.2.20 | created | needs parent UUID |
| 02 | Delete | | deleted | |

### Kea6SubnetManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create subnet | subnet=fd11:2::/64, interface=lan | created | interface required |
| 02 | Delete | | deleted | |

## Bill of Materials
- OPNsense with Kea DHCPv4 + DHCPv6 enabled on LAN
- lxc-dhcpclient-test-01 (VLAN 1320, DHCP dual-stack) for E2E lease test
- Dual-stack: ULA IPv6 fd11:2::/64 on DMZ

## Safety Boundaries
- Test subnets only (10.11.x.0/24, fd11:x::/64)
- inttest prefix on all objects
- Never modify production DHCP scopes

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 5 managers |
| Integration tests | PASS | Full lifecycle |
