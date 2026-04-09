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
| 04 | **Duplicate: same subnet** | subnet=10.11.2.0/24 (exists) | AmbiguousMatchError or API rejection | duplicate guard |

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

## CRUD Verification

API CRUD must be confirmed on the device, not just by API response.

| After CRUD | Verify with | From | Expected |
|---|---|---|---|
| Create Kea4 subnet | `ssh root@10.6.239.114 "cat /var/kea/kea-dhcp4.conf \| grep 10.11.2"` | OPNsense SSH | subnet in Kea config |
| Create Kea4 reservation | same conf file, grep MAC/IP | OPNsense SSH | reservation present |
| Kea4 lease acquired | `dhclient -v eth0` on lxc-dhcpclient-test-01 | LXC SSH | IP 10.11.2.20 assigned |
| Kea4 lease file | `ssh root@10.6.239.114 "cat /var/kea/kea-leases4.csv"` | OPNsense SSH | lease entry |
| Create Kea6 subnet | `cat /var/kea/kea-dhcp6.conf \| grep fd11:2` | OPNsense SSH | v6 subnet in config |
| Kea6 lease acquired | `dhclient -6 -v eth0` on lxc-dhcpclient-test-01 | LXC SSH | fd11:2::20 assigned |
| Reconfigure | `ssh root@10.6.239.114 "configctl kea restart"` | OPNsense SSH | Kea restarted |

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.dhcp.kea4_subnet       → Kea4SubnetManager
opnsense.managers.dhcp.kea4_reservation  → Kea4ReservationManager
opnsense.managers.dhcp.kea4_peer         → Kea4PeerManager
opnsense.managers.dhcp.kea6_subnet       → Kea6SubnetManager
opnsense.managers.dhcp.kea6_reservation  → Kea6ReservationManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.dhcp"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 5 managers |
| Integration tests | PASS | Full lifecycle |
