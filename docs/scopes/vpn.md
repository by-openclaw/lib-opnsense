<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# VPN Scope — lib-opnsense

## Diagrams

- [WireGuard Key Exchange Sequence](../../assets/diagrams/scope-vpn-sequence.puml)
- [VPN Granular Access Rules](../../assets/diagrams/scope-vpn-fw-rules.puml)
- [Network Diagram](../../assets/diagrams/scope-firewall-nwdiag.puml)
- [Class Diagram — core architecture](../../assets/diagrams/scope-lib-class.puml)

## Overview
13 managers across 3 protocols:
- WireGuard: WgServerManager (+ generate_keypair()), WgClientManager
- OpenVPN: OvpnInstanceManager (server/client roles, needs CA + cert refid)
- IPsec: IpsecConnManager, IpsecChildManager, IpsecLocalManager, IpsecRemoteManager, IpsecPskManager, IpsecKeypairManager, IpsecPoolManager, IpsecVtiManager

## Network Diagram
```
  Rune VM / Win11 Desktop
       │
       │ WAN (WireGuard/OpenVPN/IPsec tunnel)
       ▼
  ┌──────────────────────────────────┐
  │  OPNsense VPN                   │
  │                                  │
  │  WireGuard:                      │
  │    wg0: 10.10.0.1/24            │
  │    port 51820                    │
  │    peer: win11-rune 10.10.0.2   │
  │                                  │
  │  OpenVPN:                        │
  │    server mode, tun0             │
  │    needs: Trust CA + cert        │
  │                                  │
  │  IPsec:                          │
  │    conn → child + local + remote │
  │    PSK or keypair auth           │
  │    pool: 10.99.99.0/24          │
  │    VTI: plain IPs (no CIDR)     │
  └──────────────────────────────────┘
```

## Sequence Diagram — WireGuard Key Exchange
```
  Server (OPNsense)              Client (Win11/Mobile)
       │                              │
       │ 1. generate_keypair()        │
       │    → privkey + pubkey        │
       │                              │
       │ 2. Create wg0 server        │
       │    (privkey stays on server) │
       │                              │
       │ 3. Share server pubkey  ────→│
       │                              │
       │←──── 4. Client pubkey        │
       │                              │
       │ 5. Add peer (client pubkey)  │
       │                              │
       │←═══ 6. WireGuard tunnel ═══→│
```

## Managers
(list each with endpoint, match key, redact fields, module path)

WgServerManager: wireguard/server, match=name, redact=privkey/pubkey, has generate_keypair(). Module: `opnsense.managers.vpn.wg_server`
WgClientManager: wireguard/client, match=name, redact=psk. Module: `opnsense.managers.vpn.wg_client`
OvpnInstanceManager: openvpn/instances, match=description, needs CA+cert refid (not UUID). Module: `opnsense.managers.vpn.ovpn_instance`
IpsecConnManager: ipsec/connections, suffix=Connection, match=description. Module: `opnsense.managers.vpn.ipsec_conn`
IpsecChildManager: ipsec/connections, suffix=Child, match=description, needs parent conn UUID. Module: `opnsense.managers.vpn.ipsec_child`
IpsecLocalManager: ipsec/connections, suffix=Local, match=description, needs parent conn UUID. Module: `opnsense.managers.vpn.ipsec_local`
IpsecRemoteManager: ipsec/connections, suffix=Remote, match=description, needs parent conn UUID. Module: `opnsense.managers.vpn.ipsec_remote`
IpsecPskManager: ipsec/pre_shared_keys, suffix=Item, match=description, redact=Key. Module: `opnsense.managers.vpn.ipsec_psk`
IpsecKeypairManager: ipsec/key_pairs, suffix=Item, match=name, redact=privateKey. Module: `opnsense.managers.vpn.ipsec_keypair`
IpsecPoolManager: ipsec/pools, match=name. Module: `opnsense.managers.vpn.ipsec_pool`
IpsecVtiManager: ipsec/vti, match=description, plain IPs (no CIDR). Module: `opnsense.managers.vpn.ipsec_vti`

## Use Cases

### WgServerManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Generate keypair | generate_keypair() | privkey + pubkey | API key gen |
| 02 | Create server | name=inttest-wg, privkey=..., port=51820, tunneladdress=10.10.0.1/24 | created | |
| 03 | Delete | | deleted | |
| 04 | **Duplicate: same name** | name=inttest-wg (exists) | AmbiguousMatchError | duplicate guard |
| 05 | **Port: boundary min** | port=1 | created | min port |
| 06 | **Port: boundary max** | port=65535 | created | max port |
| 07 | **Error: port 0** | port=0 | FieldValidationError | below range (lib validates) |
| 08 | **Error: port > 65535** | port=125657 | FieldValidationError | above range |

> **Port field note:** `port` on WgServer/OvpnInstance uses `type: port` (strict 1-65535).
> See [port-field-reference.md](../port-field-reference.md).

### WgClientManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create peer | name=inttest-peer, pubkey=..., tunneladdress=10.10.0.2/32 | created | |
| 02 | Delete | | deleted | |

### IPsec Chain
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create conn | description=inttest-ipsec-conn, enabled=0 | created | |
| 02 | Create child | connection=<conn-uuid>, description=inttest-child | created | needs parent |
| 03 | Create local | connection=<conn-uuid> | created | |
| 04 | Create remote | connection=<conn-uuid> | created | |
| 05 | Delete chain (children first) | | deleted | order matters |

### IpsecPskManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create PSK | description=inttest-psk, Key=secret | created | redact Key |
| 02 | Delete | | deleted | |

### IpsecVtiManager
| # | Use case | Params | Expected | Validates |
|---|---|---|---|---|
| 01 | Create VTI | local=10.11.1.1, remote=10.99.99.1, tunnel_local=10.10.99.1, tunnel_remote=10.10.99.2 | created | plain IPs |
| 02 | Delete | | deleted | |

## VPN Firewall Rules — Granular Access

VPN users should access specific VLANs/hosts, NOT the whole network.
Each VPN protocol (WG, OpenVPN, IPsec) gets firewall rules on its tunnel interface.

### WireGuard → Zone Access Rules (all disabled for Phase 2)

| # | Rule | Interface | Source | Destination | Port | Action | Validates |
|---|---|---|---|---|---|---|---|
| V01 | VPN user → MGMT SSH | wg0 | 10.10.0.0/24 | 10.11.1.0/24 | 22 | pass (disabled) | SSH to management hosts |
| V02 | VPN user → DMZ HTTPS | wg0 | 10.10.0.0/24 | 10.11.2.10 | 443 | pass (disabled) | HTTPS to specific host |
| V03 | VPN user → SVC block | wg0 | 10.10.0.0/24 | 10.11.3.0/24 | any | block (disabled) | no SVC access via VPN |
| V04 | VPN user → WAN block | wg0 | 10.10.0.0/24 | any | any | block (disabled) | no internet via VPN split tunnel |
| V05 | VPN user → single host only | wg0 | 10.10.0.2/32 | 10.11.2.10 | 80,443 | pass (disabled) | per-user granular access |
| V06 | VPN → DNS (Unbound) | wg0 | 10.10.0.0/24 | 10.11.1.1 | 53 | pass (disabled) | DNS resolution through tunnel |

### Use Case: Per-User VPN Access

```
Scenario: Rune (Win11) connects via WireGuard
  - Gets IP 10.10.0.2 from tunnel
  - Can SSH to any MGMT host (10.11.1.0/24:22)
  - Can HTTPS to webdmz (10.11.2.10:443)
  - CANNOT reach SVC zone (10.11.3.0/24) — blocked
  - CANNOT reach internet via VPN — split tunnel
  - DNS queries go to OPNsense Unbound (10.11.1.1:53)
```

### Phase 3 E2E: Enable VPN rules + validate from Win11

| # | Test | Enable rule | Validate from | Expected |
|---|---|---|---|---|
| E01 | WG tunnel up | — | Win11: wg show | handshake OK, TX/RX bytes |
| E02 | SSH to MGMT | V01 | Win11: ssh 10.11.1.1 | connection OK |
| E03 | HTTPS to DMZ | V02 | Win11: curl https://10.11.2.10 | 200 OK |
| E04 | SVC blocked | V03 | Win11: curl 10.11.3.10 | timeout |
| E05 | Internet blocked | V04 | Win11: curl example.com via VPN | timeout |
| E06 | DNS works | V06 | Win11: nslookup inttest.example.com 10.11.1.1 | resolved |

## Bill of Materials
- OPNsense with WireGuard enabled
- Trust/PKI: CA + cert for OpenVPN (see trust scope)
- E2E: Rune VM or Win11 desktop as VPN client (WAN side)
- E2E: Rune Win11 desktop as WireGuard client (WAN side, 10.100.0.x)
- VPN VLAN (optional): VLAN 1340, 10.11.4.0/24 for dedicated VPN client subnet (if isolating VPN clients from other zones)
- No additional LXC needed

## Safety Boundaries
- All VPN tunnels created disabled (enabled=0)
- inttest- prefix on all names/descriptions
- WireGuard: test port 51820, test subnet 10.10.0.0/24
- IPsec: test IPs from 10.99.x.x range
- VTI: plain IPs only (API rejects CIDR)
- Never touch production VPN tunnels

## Logging

Logger path follows package structure for Loki/Promtail filtering:
```
opnsense.managers.vpn.wg_server      → WgServerManager
opnsense.managers.vpn.wg_client      → WgClientManager
opnsense.managers.vpn.ovpn_instance  → OvpnInstanceManager
opnsense.managers.vpn.ipsec_conn     → IpsecConnManager
opnsense.managers.vpn.ipsec_child    → IpsecChildManager
opnsense.managers.vpn.ipsec_local    → IpsecLocalManager
opnsense.managers.vpn.ipsec_remote   → IpsecRemoteManager
opnsense.managers.vpn.ipsec_psk      → IpsecPskManager
opnsense.managers.vpn.ipsec_keypair  → IpsecKeypairManager
opnsense.managers.vpn.ipsec_pool     → IpsecPoolManager
opnsense.managers.vpn.ipsec_vti      → IpsecVtiManager
```

Filter in Loki: `{job="opnsense"} |= "opnsense.managers.vpn"`

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 13 managers |
| Integration tests | PASS | Full lifecycle |
