# BY-SYSTEMS Firewall Specification — OPNsense single-source-of-truth

> **Status:** DRAFT v0.1 — 2026-05-23
> **Scope:** End-state target for all BY-SYSTEMS OPNsense firewalls (test + prod, single-FW + HA Phase 2).
> **Audience:** lib-opnsense maintainers, Ansible playbook authors, NetOps.
> **Read this before**: writing any new lib-opnsense manager, drafting any Ansible role, modifying any seed XML, deploying any new FW.

This document defines the **target state** of every layer of our OPNsense FW config. It is the executable contract between:
- the **seed-ISO builder** (`infra-terraform-proxmox/modules/vm-opnsense/seed/build-seed.py`) — bootstraps initial config
- **lib-opnsense** (this repo) — Day-2 idempotent management via MVC REST API
- **Ansible playbooks** (planned `playbooks/opnsense-*.yml`) — orchestrates lib-opnsense managers
- **Integration tests** (`tests/integration/`) — verifies live FW matches spec

Every change to a running FW must be traceable to a section in this document. Every section names its responsible lib-opnsense scope, its Ansible role, and its integration test reference.

---

## Section 1 — Topology & Interface Assignments

### Target state

```
Internet (Proximus fiber, VLAN 10 tagged)
         │
         ▼ (Proxmox host: nic0.10 → vmbrWAN1)
    ┌────────────────────┐                     Internet (Telenet fiber, untagged)
    │  WAN1 = pppoe0     │                              │
    │  IPv4 PPPoE dyn    │                              ▼ (Proxmox host: nic1 → vmbrWAN2)
    │  IPv6 /56 PD       │                     ┌────────────────────┐
    │  (failover)        │                     │  WAN2 = vtnet3     │
    └────────┬───────────┘                     │  IPv4 213.214.47.222/29 (static)
             │                                 │  IPv6 2a02:1802:21::2/64 (static, /48 routed)
             │                                 │  (primary default GW)
             │                                 └────────┬───────────┘
             │                                          │
             └──────────┬───────────────────────────────┘
                        │
              ┌─────────▼─────────┐
              │  OPNsense FW      │
              │  vm-opns-test-01  │  (single-FW now; HA Phase 2 = two VMs with CARP)
              └─┬────────────┬────┘
                │            │
       ┌────────▼──┐    ┌────▼──────────────┐
       │ LAN       │    │ OPT1 = LAN_TRUNK   │
       │ = vtnet1  │    │ = vtnet0 (SDN trunk)
       │ = OOB mgmt│    │   parent of opt4..N│
       │ 10.6.x.x  │    │   (VLAN sub-ifs)   │
       └───────────┘    └────────────────────┘
```

### Interface slot cascade (OPNsense identifiers)

| OPNsense slot | Device  | Role           | IPv4                       | IPv6                                |
|---------------|---------|----------------|----------------------------|-------------------------------------|
| `wan`         | pppoe0  | WAN1 Proximus  | PPPoE dynamic              | DHCPv6 over PPP, /56 PD             |
| `lan`         | vtnet1  | OOB management | DHCP from upstream         | static GUA from Telenet /48         |
| `opt1`        | vtnet0  | SDN trunk      | 10.11.1.1/24 (test)        | static GUA from Telenet /48         |
| `opt2`        | vtnet2  | WAN1_Parent    | none (raw)                 | none                                |
| `opt3`        | vtnet3  | WAN2 Telenet   | 213.214.47.222/29 (static) | 2a02:1802:21::2/64 (static)         |
| `opt4`        | vlan2010| OPS            | 10.11.201.1/24             | 2a02:1802:21:2010::1/64             |
| `opt5`        | vlan2020| DMZ            | 10.11.202.1/24             | 2a02:1802:21:2020::1/64             |
| `opt6`        | vlan2030| SVC            | 10.11.203.1/24             | 2a02:1802:21:2030::1/64             |
| `opt7`        | vlan2040| VPN            | 10.11.204.1/24             | 2a02:1802:21:2040::1/64             |
| `opt8`        | vlan2100| IoT            | 10.11.210.1/24             | 2a02:1802:21:2100::1/64             |
| `opt9`        | vlan2110| VoIP           | 10.11.211.1/24             | 2a02:1802:21:2110::1/64             |
| `opt10`       | vlan2200| Storage        | 10.11.220.1/24             | 2a02:1802:21:2200::1/64             |
| `opt11`       | vlan2300| Media          | 10.11.230.1/24             | 2a02:1802:21:2300::1/64             |
| `opt12`       | vlan2320| GAMING         | 10.11.232.1/24             | 2a02:1802:21:2320::1/64             |
| `opt13`       | vlan2400| CCTV           | 10.11.240.1/24             | 2a02:1802:21:2400::1/64             |

VLAN tag aligned with v6 sub-prefix for readability (`vlan2010` ↔ `2a02:1802:21:**2010**::/64`).

### Responsibility

- **Bootstrap (initial seed):** `build-seed.py` renders `<interfaces>`, `<vlans>`, `<ppps>`, `<gateways>` from `seeds/vm-opns-*.json`.
- **Day-2 management:** `lib-opnsense.managers.interfaces.VlanManager`, `LoopbackManager`, `BridgeManager`, `LaggManager`, `VxlanManager`. PPP/PPPoE has no MVC endpoint → managed by seed only (re-render + reseed for changes).
- **Ansible role:** `roles/opnsense_interfaces`.
- **Integration test:** `tests/integration/interfaces/test_full_topology.py` — asserts all slots assigned + correct IPs.

### HA Phase 2 placeholders

- vm-opns-test-01 (MASTER): IPs as above.
- vm-opns-test-02 (BACKUP): same NICs, IPs +1 (e.g. WAN2 = `.221`, internal `.2`).
- CARP VIPs (Phase 2): `.220` on WAN2, `.254` on every internal VLAN — the IPs clients use as default gateway.
- pfsync interface: new bridge `vmbrPFSYNC`, /29 between MASTER + BACKUP only.

---

## Section 2 — Address Plan (IPv4 + IPv6, public + private)

### Public IPv4

| Subnet                | Allocation                                                           |
|-----------------------|----------------------------------------------------------------------|
| `213.214.47.216/29` (Telenet) | `.217 gw, .218 pfsense01 (legacy → migrate behind Traefik on .222), .219 nginx-odoo (legacy), .220+.221 reserved HA Phase 2, .222 OPNsense MASTER` |
| WAN1 PPPoE (Proximus) | dynamic (publish via DDNS to `wan1.by-research.be`)                  |

### Public IPv6 (Telenet /48)

| Block                          | Use                                                    |
|--------------------------------|--------------------------------------------------------|
| `2a02:1802:21::/48`            | Routed to OPNsense (via `::2`) after pfsense IPv6 disabled |
| `2a02:1802:21::/64`            | WAN-side direct link (Telenet ↔ OPNsense), do NOT use internally |
| `2a02:1802:21:NNNN::/64`       | One /64 per internal VLAN, `NNNN` = VLAN tag for readability |
| `2a02:1802:21:0001::/64`       | LAN (OOB mgmt) /64                                     |
| `2a02:1802:21:0010::/64`       | OPT1 trunk /64 (informational; no clients normally)    |

### Public IPv6 (Proximus /56 PD — failover only)

When Telenet path fails: Track-Interface IPv6 on internal VLANs would fall back to Proximus /56 PD. **Disabled by default** in spec; enable per-VLAN via lib-opnsense `interfaces.InterfaceManager` if needed for specific failover scenarios.

### Private IPv4 (RFC1918)

| Network            | Use                                                  |
|--------------------|------------------------------------------------------|
| `10.1.0.0/16`      | Prod supernet (SDN trunk + VLANs on prod FW)         |
| `10.11.0.0/16`     | Test supernet (vm-opns-test-01)                      |
| `10.6.224.0/20`    | OOB management (Proxmox hosts + FW mgmt + admin workstations) |
| `10.100.0.0/24`    | Tailscale (external admin/automation reach, *not* used inside FW design) |

Per-VLAN subnets follow `10.<env>.<vlan/10>.0/24` convention (e.g. test VLAN 2010 → 10.11.201.0/24).

### Private IPv6 (ULA fd11::/16, optional dual-stack)

Reserved for offline / air-gapped scenarios. Not deployed by default — Telenet /48 provides stable GUA.

### Responsibility

- **Authoritative source:** secret files
  - `secrets/net-isp-telenet.json` — IPv4 /29 + IPv6 /48 + DNS
  - `secrets/net-isp-proximus-pppoe.json` — PPPoE creds + /56 PD hint
- **Bootstrap:** `build-seed.py` reads secrets at build time.
- **Day-2 verification:** `lib-opnsense.managers.interfaces.InterfaceManager` — confirms each VLAN has expected IPv4 + IPv6.
- **Integration test:** `tests/integration/interfaces/test_address_plan.py`.

---

## Section 3 — Gateways + Failover

### Target state

| Gateway name    | Interface | Protocol | Address               | Monitor              | Default | Tier |
|-----------------|-----------|----------|-----------------------|----------------------|---------|------|
| `WAN2GW`        | opt3      | inet     | 213.214.47.217        | 213.214.47.217       | YES     | 1    |
| `WAN2GWv6`      | opt3      | inet6    | 2a02:1802:21::1       | 2a02:1802:21::1      | YES     | 1    |
| `WAN1_PPPoE`    | wan       | inet     | dynamic               | 1.1.1.1              | no      | 2    |
| `WAN1_DHCPv6`   | wan       | inet6    | dynamic               | 2606:4700:4700::1111 | no      | 2    |
| `VPNEXPRESS_US` | opt7 (VPN)| inet     | dynamic (WG peer)     | -                    | no      | -    |
| `VPNEXPRESS_FR` | opt7 (VPN)| inet     | dynamic (WG peer)     | -                    | no      | -    |

### Gateway groups (load balance + failover)

- `GW_DEFAULT_V4`: tier 1 = WAN2GW, tier 2 = WAN1_PPPoE → automatic failover to Proximus if Telenet down.
- `GW_DEFAULT_V6`: tier 1 = WAN2GWv6, tier 2 = WAN1_DHCPv6.
- `GW_VPN_US`: tier 1 = VPNEXPRESS_US (for GAMING / MEDIA streaming geo-bound to US).
- `GW_VPN_FR`: tier 1 = VPNEXPRESS_FR (for content geo-bound to FR).

### Responsibility

- **Bootstrap:** `build-seed.py` emits `<gateways><gateway_item>` for static (WAN2*). Dynamic (WAN1_PPPoE, WAN1_DHCPv6) auto-created by OPNsense from PPPoE/DHCP config. Gateway groups (`GW_DEFAULT_*`) emitted by seed.
- **Day-2:** `lib-opnsense.managers.routing.GatewayManager`, `GatewayGroupManager`.
- **Ansible role:** `roles/opnsense_gateways`.
- **Integration test:** `tests/integration/routing/test_gateways.py` — fails over by disabling WAN2, asserts default route migrates to WAN1.

---

## Section 4 — Aliases (foundation for all rules)

Rules MUST reference aliases, never raw IPs/networks. This makes rule audits possible and renumbering safe.

### Network aliases

| Alias name        | Type    | Members (IPv4 + IPv6)                                                  |
|-------------------|---------|------------------------------------------------------------------------|
| `NET_OOB`         | network | `10.6.224.0/20`                                                        |
| `NET_TAILSCALE`   | network | `10.100.0.0/24, fd7a:115c:a1e0::/48`                                   |
| `NET_OPS`         | network | `10.11.201.0/24, 2a02:1802:21:2010::/64`                               |
| `NET_DMZ`         | network | `10.11.202.0/24, 2a02:1802:21:2020::/64`                               |
| `NET_SVC`         | network | `10.11.203.0/24, 2a02:1802:21:2030::/64`                               |
| `NET_VPN`         | network | `10.11.204.0/24, 2a02:1802:21:2040::/64`                               |
| `NET_IOT`         | network | `10.11.210.0/24, 2a02:1802:21:2100::/64`                               |
| `NET_VOIP`        | network | `10.11.211.0/24, 2a02:1802:21:2110::/64`                               |
| `NET_STORAGE`     | network | `10.11.220.0/24, 2a02:1802:21:2200::/64`                               |
| `NET_MEDIA`       | network | `10.11.230.0/24, 2a02:1802:21:2300::/64`                               |
| `NET_GAMING`      | network | `10.11.232.0/24, 2a02:1802:21:2320::/64`                               |
| `NET_CCTV`        | network | `10.11.240.0/24, 2a02:1802:21:2400::/64`                               |
| `NET_TRUSTED`     | nested  | OPS + SVC + STORAGE + VOIP + Tailscale                                 |
| `NET_UNTRUSTED`   | nested  | IoT + GUEST + CCTV                                                     |
| `NET_INTERNAL`    | nested  | All NET_* internal (everything except WAN/OOB)                         |
| `RFC1918`         | network | `10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7`                  |
| `BOGONS_V4`       | url     | OPNsense built-in bogon list (auto-updated)                            |
| `BOGONS_V6`       | url     | OPNsense built-in bogon list (auto-updated)                            |

### Host aliases (specific machines)

| Alias name           | Members                                                |
|----------------------|--------------------------------------------------------|
| `HOST_NAS`           | Synology NAS IPs (IPv4 + IPv6)                         |
| `HOST_PROXMOX_POC`   | `10.6.224.105, 2a02:1802:21:1::5` (when added)         |
| `HOST_PROXMOX_PROD`  | `10.6.224.5, 2a02:1802:21:1::6` (when added)           |
| `HOST_TRAEFIK`       | Internal Traefik VM IP (TBD)                           |
| `HOST_GITLAB`        | GitLab CE VM IP                                        |
| `HOSTS_BLOCKED`      | dynamic list — pf-blockerNG / Spamhaus DROP            |

### Port aliases

| Alias name      | Ports                                          |
|-----------------|------------------------------------------------|
| `PORTS_SSH`     | `22`                                           |
| `PORTS_WEB`     | `80, 443`                                      |
| `PORTS_MGMT`    | `22, 443, 80` (OPNsense WebGUI + SSH)          |
| `PORTS_VPN_WG` | `51820, 51821` (OpenVPN, WireGuard server)      |
| `PORTS_DNS`     | `53` (TCP+UDP), `853` (DoT), `443` (DoH)       |
| `PORTS_VOIP`    | `5060 (SIP), 10000-20000 (RTP)`                |
| `PORTS_QUIC`    | `443 UDP`                                      |

### Responsibility

- **Bootstrap:** seed includes a minimal alias set (NET_OOB, RFC1918, BOGONS_*, NET_INTERNAL) so default-deny rules can reference them.
- **Day-2:** `lib-opnsense.managers.firewall.AliasManager` — full CRUD with composite match keys (name + type).
- **Ansible role:** `roles/opnsense_aliases`.
- **Integration test:** `tests/integration/firewall/test_aliases.py`.

---

## Section 5 — Firewall Rules (alias-referenced, never raw IP)

### Default posture

- **Default deny on every interface.** Hidden internal block rule fires last; rules are explicit pass.
- **Stateful by default.** All pass rules `quick=1` + keep state.
- **IPv4 and IPv6 separately for each rule.** Some auto-generate v6 from v4 (anti-lockout etc.), most need explicit duplicate.

### Per-interface rule set

**WAN1 (PPPoE) and WAN2 (Telenet) — same posture:**
- `pass` ICMP echo (size-limited, rate-limited) for monitoring
- `pass` to `(self):443` from `NET_TAILSCALE` (for lib-opnsense automation)
- `pass` to `(self):51820 UDP` (WireGuard server endpoint)
- `pass` NAT 1:1 rules to internal services (see Section 6)
- `block` everything else (default deny logged)

**LAN (OOB management):**
- Anti-lockout rule (hidden auto, allows admin from LAN to FW)
- `pass` from `NET_OOB` to `any` (admin reaches anywhere)
- `pass` from `NET_OOB` to `(self):443+:22` (explicit, even though anti-lockout covers it)
- No restrictions — OOB is trusted

**OPT1 (LAN_TRUNK):** No rules — this is just the trunk parent, traffic transits via VLAN sub-interfaces.

**OPS (admin/operator workstations):**
- `pass` from `NET_OPS` to `NET_INTERNAL` (manage anything internal)
- `pass` from `NET_OPS` to `any:80,443` (full internet access)
- `pass` from `NET_OPS` to `any` (admin override — trusted)

**DMZ (public-facing services):**
- `pass` from `NET_DMZ` to `any:80,443,53` (outbound only common services)
- `block` from `NET_DMZ` to `NET_INTERNAL` (DMZ MUST NOT initiate to internal)
- `pass` from any to `HOST_TRAEFIK:80,443` (inbound via NAT 1:1 — see Section 6)

**SVC (backend services):**
- `pass` from `NET_SVC` to `HOST_NAS:any` (database + storage)
- `pass` from `NET_SVC` to `any:80,443,53` (outbound updates)
- `block` from `NET_SVC` to internet by default (security)

**VPN (road warrior subnet):**
- `pass` from `NET_VPN` to `NET_INTERNAL` (VPN users reach internal — see Section 7 for user-based filtering)
- `pass` from `NET_VPN` to `any` (full internet)

**IoT:**
- `pass` from `NET_IOT` to `any:53,123,80,443` (DNS, NTP, HTTP/S only)
- `block` from `NET_IOT` to `NET_INTERNAL` (no internal reachability)
- `block` outbound `NET_IOT` to RFC1918 (no random LAN scanning)

**VoIP:**
- `pass` from `NET_VOIP` to `any:5060,10000-20000` (SIP + RTP)
- `pass` from `NET_VOIP` to `any:53,80,443` (provisioning, updates)
- `block` else
- Priority queue (see traffic shaping — TODO future section)

**Storage:**
- `pass` from `NET_STORAGE` to `any:80,443,53` (cloud backup, updates)
- `pass` from `NET_STORAGE` to `NET_TRUSTED:445,2049,nfs ports`
- `block` else

**Media:**
- `pass` from `NET_MEDIA` to `any` (streaming clients need wide access)
- Policy route via `GW_VPN_US` for traffic to known streaming geo-locked services (Section 3)

**GAMING:**
- `pass` from `NET_GAMING` to `any` (games need wide reachability)
- Policy route via `GW_VPN_US` for region-locked services
- Priority queue for latency

**CCTV:**
- `block` from `NET_CCTV` to `any` (cameras don't need internet)
- `pass` from `NET_CCTV` to `HOST_NAS:445,nfs` (record to storage)
- `pass` from `NET_TRUSTED` to `NET_CCTV:80,443,554` (viewers reach cameras)

### Floating rules (apply to all interfaces)

- `block` source RFC1918 inbound on WAN1+WAN2 (block_private + block_bogons toggles, but also explicit floating rule)
- `block` outbound SMB (445), NetBIOS (137-139) to internet from any interface — leak prevention
- `pass` ICMPv6 (RFC 4890 essentials — neighbour discovery, MLD, etc.)
- `block` non-stateful TCP flags (XMAS, NULL, FIN+SYN, etc.)
- `block` source-routed packets (IP options 7, 137)

### Responsibility

- **Bootstrap:** seed renders **only** anti-lockout + Tailscale admin pass rule, so the FW is reachable post-install. Everything else applied by Day-2.
- **Day-2:** `lib-opnsense.managers.firewall.FwFilterManager`. Rules indexed by composite key (description + interface + sequence).
- **Ansible role:** `roles/opnsense_rules`.
- **Integration test:** `tests/integration/firewall/test_rules_matrix.py` — generates test traffic between every pair of VLANs, asserts allow/block matches spec.

---

## Section 6 — NAT (outbound + 1:1 + port forwards)

### Outbound NAT — hybrid (per-WAN auto + custom overrides)

- **Mode:** Hybrid (manual rules first, then auto for unmatched)
- **Auto:** OPNsense generates per-WAN outbound NAT for each internal subnet → source-masquerade to WAN egress IP
- **Custom rule examples:**
  - Force VoIP outbound via WAN2 (lower jitter): `from NET_VOIP → any` egress `opt3 (WAN2)` translate to `213.214.47.222`
  - Force GAMING via VPN: handled by gateway group, not NAT (Section 3)

### NAT 1:1 (Telenet static IPs → internal servers)

| Public IP            | Internal target              | Use                             |
|----------------------|------------------------------|---------------------------------|
| `213.214.47.222`     | OPNsense itself              | FW management + WG server endpoint |
| `213.214.47.220`     | (reserved HA Phase 2 CARP)   | -                               |
| `213.214.47.221`     | (reserved HA Phase 2 BACKUP) | -                               |
| `213.214.47.218`     | pfsense01 (legacy)           | retire after Traefik migration  |
| `213.214.47.219`     | HOST_TRAEFIK (planned)       | Reverse proxy — host-based routing for all web services |

IPv6: NOT needed (every internal device has its own public v6 via /48 carving — true end-to-end).

### Port forwards

Only for services NOT covered by NAT 1:1:
- `213.214.47.222:51820 UDP → OPNsense WG server` (port forward not needed if WG binds to the WAN IP directly, but listed for clarity)

### Responsibility

- **Bootstrap:** seed sets NAT outbound mode = `hybrid`. No NAT 1:1 / port forwards in seed (applied Day-2 once services exist).
- **Day-2:** `lib-opnsense.managers.firewall.NatOutboundManager`, `NatOneToOneManager`, `NatPortForwardManager`.
- **Ansible role:** `roles/opnsense_nat`.
- **Integration test:** `tests/integration/firewall/test_nat.py` — outbound from each VLAN reaches a test server via expected WAN IP.

---

## Section 7 — Users + Groups + ACL

### Local groups

| Group         | Purpose                                                         | Privileges                                       |
|---------------|-----------------------------------------------------------------|--------------------------------------------------|
| `admins`      | Full FW admin (matches OPNsense built-in)                       | `page-all`                                       |
| `operators`   | Day-to-day ops: read all, edit rules + NAT + interfaces         | per-page list (firewall, interfaces, services)   |
| `audit`       | Read-only across FW                                             | `page-dashboard-all`, read-only on others        |
| `vpn_users`   | WireGuard road warriors — only consume VPN, no admin            | none (just used in WG client config + rules)     |
| `ddns_writers`| Service account allowed to update DDNS via API                  | api access to ddns endpoints only                |

### User-to-firewall-rule mapping

OPNsense doesn't natively tie users to interface rules, BUT:
- WG client peers get individual IPs in `NET_VPN`
- Tag each peer's source IP with a host alias (`VPN_USER_alice`, `VPN_USER_bob`, etc.)
- Rules can reference these aliases for per-user access control

Example:
- `VPN_USER_alice` = 10.11.204.10 → allowed `NET_INTERNAL` (full internal access)
- `VPN_USER_guest` = 10.11.204.50 → allowed only `NET_DMZ:80,443` (limited)

### Service accounts

| Account     | Use                                                | Auth                              |
|-------------|----------------------------------------------------|-----------------------------------|
| `root`      | Emergency only; SSH disabled by default            | seed password (rotated)           |
| `by-rune`   | Day-to-day SSH for emergency console               | ED25519 key from secret store     |
| `svc-rune`  | Ansible / lib-opnsense automation                  | API key (HMAC), no shell          |
| `svc-opus`  | Audit / read-only ingestion                        | API key (HMAC), no shell          |
| `svc-ddns`  | DDNS updater                                       | API key, only ddns endpoint perms |

### Responsibility

- **Bootstrap:** seed creates `admins` group + `root` user only. Other users + groups via Day-2.
- **Day-2:** `lib-opnsense.managers.auth.AuthUserManager`, `AuthGroupManager`, `AuthPrivManager`, `AuthApiKeyManager`.
- **Ansible role:** `roles/opnsense_users` — reads from `secrets/fw-users.yml` + per-user pubkey files.
- **Integration test:** `tests/integration/auth/test_user_lifecycle.py`.

---

## Section 8 — VPN (WireGuard server + client, OpenVPN optional)

### WireGuard server (road warriors)

- **Listen:** WAN1 (DDNS) + WAN2 (static) on UDP `51820`
- **Tunnel subnet:** `10.11.204.0/24` + `2a02:1802:21:2040::/64` (VPN VLAN)
- **DNS pushed:** internal Unbound IP (so VPN users get split-DNS)
- **Allowed-IPs from server side:** `NET_INTERNAL` (clients can reach all internal — refined by per-user rules in Section 5+7)
- **Per-client config:** managed via `lib-opnsense.managers.vpn.WireGuardClientManager`
- **Persistent keepalive:** 25 s (NAT traversal)

### WireGuard client → VPNExpress (egress for specific VLANs)

- **VPNEXPRESS_US peer:** WG tunnel to provider's US endpoint; gateway `VPNEXPRESS_US` (Section 3)
- **VPNEXPRESS_FR peer:** ditto, FR endpoint
- **Use case:** GAMING + MEDIA VLANs policy-routed through these (for Netflix US, region-locked content)
- **Kill switch:** if VPN tunnel down, traffic NOT to leak via native WAN — explicit block rule on those VLANs to `any` except via VPN gateway

### OpenVPN (deferred)

OpenVPN supported by lib-opnsense but not deployed by default — WG covers all use cases more efficiently.

### Responsibility

- **Bootstrap:** seed creates empty WG instance (placeholder).
- **Day-2:** `lib-opnsense.managers.vpn.WireGuardServerManager`, `WireGuardClientManager`, `WireGuardPeerManager`.
- **Ansible role:** `roles/opnsense_wireguard`.
- **Integration test:** `tests/integration/vpn/test_wireguard.py` — connects a test peer, verifies internal reachability.

---

## Section 9 — DNS (Unbound + DoT/DoH + per-VLAN policies)

### Unbound configuration

- **Mode:** recursive resolver (not forwarder by default)
- **Listen:** all internal interfaces, port 53 TCP+UDP
- **DNSSEC:** ON (validate all responses)
- **Upstream forwarders (when forwarding mode used):**
  - DoT (TLS) to Cloudflare `1.1.1.1@853` + `1.0.0.1@853`
  - DoT to Quad9 `9.9.9.9@853` (fallback)
  - IPv6: `2606:4700:4700::1111@853`, `2620:fe::9@853`
- **Local zones (authoritative):**
  - `by-research.be` — internal-only A/AAAA records for lab gear
  - `by-systems.be` — internal-only mirror of public zone (split-horizon)
  - `*.local.by-research.be` — wildcards for ad-hoc dev hosts
- **Block lists (per-VLAN policy):**
  - `NET_IOT, NET_GUEST` → load Steven Black ads/malware blocklist (block at resolution time)
  - `NET_OPS, NET_SVC` → no block list (admin sees real responses)
  - `NET_GAMING, NET_MEDIA` → minimal blocklist (just malware, no ads)
- **Negative cache:** 300 s
- **Min TTL:** 60 s (clamp upstream low-TTL replies for stability)

### DDNS clients

See Section 10.

### Responsibility

- **Bootstrap:** seed creates Unbound instance with DoT + DNSSEC enabled, listening on LAN + OPT1.
- **Day-2:** `lib-opnsense.managers.dns.UnboundGeneralManager`, `UnboundAccessListManager`, `UnboundDomainOverrideManager`, `UnboundHostOverrideManager`, `UnboundForwardManager`, `UnboundBlocklistManager` (if plugin installed).
- **Ansible role:** `roles/opnsense_dns`.
- **Integration test:** `tests/integration/dns/test_unbound.py` — query from each VLAN, verify expected resolution + blocklist behavior.

---

## Section 10 — DDNS

### Targets

| Hostname (Cloudflare zone)         | Source             | A record updates | AAAA record updates |
|------------------------------------|--------------------|------------------|---------------------|
| `wan1.by-research.be`              | WAN1 PPPoE dynamic | YES (every change)| YES (every change)  |
| `wan2.by-research.be`              | WAN2 Telenet static| set once         | set once            |
| `vpn.by-research.be`               | failover (WAN2→WAN1 if WAN2 down) | YES on failover | YES on failover |

### Implementation

- **Tool:** `os-ddclient` plugin (OPNsense MVC)
- **API:** Cloudflare API token (scoped per-zone, in secret store)
- **Secret:** `secrets/app-cloudflare-by-research-be.json`
- **Update trigger:** OPNsense `newwanip` event hook → `ddclient` re-runs

### Responsibility

- **Bootstrap:** seed leaves ddns inactive (no records).
- **Day-2:** `lib-opnsense.managers.dns.DdnsClientManager`. Cloudflare token read from secret at apply time.
- **Ansible role:** `roles/opnsense_ddns`.
- **Integration test:** `tests/integration/dns/test_ddns.py` — force a WAN IP change (re-dial PPPoE), assert Cloudflare A/AAAA updated within 60s.

---

## Section 11 — Cloud integration (Contabo VPS)

### Topology

```
              ┌──────────────┐
              │  OPNsense FW │  WG server: listens on wan1.by-research.be:51820
              │              │  Tunnel subnet: 10.11.204.0/24 + 2a02:1802:21:2040::/64
              └──────┬───────┘
                     │ WG mesh
       ┌─────────────┼─────────────┐
       │             │             │
   ┌───▼──┐     ┌───▼──┐     ┌───▼──┐
   │ VPS1 │     │ VPS2 │     │ VPSn │   Contabo — each has pub IP + WG client
   │ ::40 │     │ ::41 │     │ ::4n │
   └──────┘     └──────┘     └──────┘
```

### Per-VPS config

- **Tunnel IP:** `10.11.204.40+N` and `2a02:1802:21:2040::40+N`
- **AllowedIPs server-side:** `10.11.204.40+N/32, 2a02:1802:21:2040::40+N/128`
- **AllowedIPs client-side:** `10.11.0.0/16, 2a02:1802:21::/48` (reach internal services)
- **Selective routing on VPS:** outbound traffic uses VPS pub IP; only management + monitoring + secret retrieval tunnels through WG
- **Persistent keepalive:** 25 s

### Use cases

- **Management:** Ansible runs from internal Ansible host, reaches VPS via WG tunnel (no need to expose VPS SSH publicly)
- **Monitoring:** Prometheus scrapes VPS metrics over WG
- **Backup:** rsync VPS data over WG to internal NAS
- **Secret retrieval:** VPS fetches secrets from internal Vault over WG

### Responsibility

- **Bootstrap:** seed leaves WG server placeholder.
- **Day-2:** `lib-opnsense.managers.vpn.WireGuardPeerManager` for each VPS peer. VPS-side WG client managed by separate Ansible role `roles/contabo_wireguard_client`.
- **Integration test:** `tests/integration/vpn/test_contabo_mesh.py` — verify each VPS reachable via tunnel IP after peer addition.

---

## Section 12 — Backup / restore + secrets

### Config backup

- **Daily:** OPNsense's built-in nightly config backup → uploaded to OOB NAS via NFS (or rsync to a backup VM)
- **Retention:** 100 revisions (OPNsense default) + 30 days off-FW
- **Trigger on config change:** also push to remote backup immediately

### Secret rotation

| Secret                  | Rotation procedure                                                       |
|-------------------------|--------------------------------------------------------------------------|
| `pppoe_password`        | Edit `secrets/net-isp-proximus-pppoe.json` → rebuild seed → reseed FW    |
| Telenet IPs             | Edit `secrets/net-isp-telenet.json` → rebuild seed → reseed FW           |
| API tokens (svc-rune)   | Rotate via `lib-opnsense.managers.auth.AuthApiKeyManager.rotate()`        |
| WG private keys         | Rotate via `lib-opnsense.managers.vpn.WireGuardServerManager.rotate_keys()` (issues new pubkey, requires client config update) |
| Root password           | Rotate via `lib-opnsense.managers.auth.AuthUserManager.set_password()`   |
| Cloudflare DDNS token   | Rotate via Cloudflare UI → update `secrets/app-cloudflare-by-research-be.json` → re-apply ddns config |

### Secret storage

- **Location:** `~/.openclaw/workspace/infra/secrets/*.json`
- **Permissions:** `0600`, owned by operator
- **Git:** gitignored via workspace `.gitignore`
- **Future:** migration to HashiCorp Vault (Phase 2) — `AppRoleCredentialProvider` already stub'd in lib-opnsense

### Responsibility

- **Backup:** OPNsense built-in + external `cron + scp` to NAS.
- **Secret management:** consumer responsibility (build-seed + lib-opnsense both read secret files at build/apply time).
- **No plaintext secrets in:** source code, terminal output, log files, commit history.

---

## Sign-off

This spec is the single source of truth for BY-SYSTEMS OPNsense FW configuration.

Changes to this document require:
1. PR review by NetOps + at least one operator
2. Update of the corresponding lib-opnsense manager(s) if XML structure or MVC API changes
3. Update of integration tests to match new spec
4. Reseed (or Day-2 apply) of the running FW within 24 h of merge

Open questions / future sections (TODO before v1.0):
- Traffic shaper config (per-VLAN bandwidth, fq_codel pipes for VoIP/Gaming priority)
- Suricata IPS rules (which VLANs, which rule sets)
- HAProxy reverse-proxy config (if not deferred entirely to Traefik)
- VLAN-to-port mapping on the HPE V1910-48G switch (cross-doc — sits in `infra-network-switches/`)
- Per-VLAN DHCP server (Kea) lease policies, reservations, option pushes
- Multicast / mDNS reflector config (GAMING ↔ MEDIA for Chromecast)
- IPv6 RA (radvd / dhcp6d) policy per-VLAN
- Layer 7 inspection (Zenarmor)
- Compliance: BY-SYSTEMS RAID tracking for any spec deviation
