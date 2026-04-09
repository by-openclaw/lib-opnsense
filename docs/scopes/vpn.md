<!--
  Copyright BY-SYSTEMS SRL
  SPDX-License-Identifier: MIT
  https://github.com/by-openclaw/lib-opnsense
-->

# VPN Scope — lib-opnsense

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

## Bill of Materials
- OPNsense with WireGuard enabled
- Trust/PKI: CA + cert for OpenVPN (see trust scope)
- E2E: Rune VM or Win11 desktop as VPN client (WAN side)
- No additional LXC needed

## Safety Boundaries
- All VPN tunnels created disabled (enabled=0)
- inttest- prefix on all names/descriptions
- WireGuard: test port 51820, test subnet 10.10.0.0/24
- IPsec: test IPs from 10.99.x.x range
- VTI: plain IPs only (API rejects CIDR)
- Never touch production VPN tunnels

## Test Status
| Test | Status | Notes |
|------|--------|-------|
| Unit tests | PASS | All 13 managers |
| Integration tests | PASS | Full lifecycle |
