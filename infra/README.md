<!--
  Copyright (c) 2026 BY-SYSTEMS SRL. All rights reserved.
  SPDX-License-Identifier: MIT
  Repo: https://github.com/by-openclaw/lib-opnsense
-->

# Integration Test Infrastructure

Terraform config to provision the test environment for lib-opnsense integration tests.

**Source of truth:** [`by-openclaw/infra-terraform-proxmox`](https://github.com/by-openclaw/infra-terraform-proxmox) `environments/test/`

This directory contains a **reference copy** of the SDN + VM + LXC config needed to run integration tests. If Proxmox exists, a developer can apply this to get a working test zone.

## Prerequisites

- Proxmox VE node with `bpg/proxmox` provider access
- OPNsense 26.1.2 ISO on `poc-iso` storage
- Debian 12 LXC template on `local` storage

## What it creates

| Resource | Name | VMID/VLAN | Purpose |
|---|---|---|---|
| SDN Zone | test | — | Test environment VLAN zone |
| VNet | tmgmt | VLAN 2010 | Management (10.11.1.0/24) |
| VNet | tdmz | VLAN 2020 | DMZ (10.11.2.0/24) |
| VNet | tsvc | VLAN 2030 | Services (10.11.3.0/24) |
| VNet | tvpn | VLAN 2040 | VPN (10.11.4.0/24) |
| VNet | tiot | VLAN 2100 | IoT (10.11.10.0/24) |
| VNet | tvoip | VLAN 2110 | VoIP (10.11.11.0/24) |
| VNet | tstor | VLAN 2200 | Storage (10.11.20.0/24) |
| VNet | tmedia | VLAN 2300 | Media (10.11.30.0/24) |
| VNet | tcctv | VLAN 2400 | CCTV (10.11.40.0/24) |
| VM | vm-fw-test-01 | 1100 | OPNsense test firewall (4 NICs) |
| LXC | lxc-webdmz-test-01 | 1500 | HTTP target for DNAT tests |
| LXC | lxc-websrv-test-01 | 1501 | Internal service for routing tests |
| LXC | lxc-dhcpclient-test-01 | 1502 | DHCP lease validation |

## OPNsense Bootstrap (manual, console)

After `terraform apply` creates VM 1100:

1. Open Proxmox noVNC console for vm-fw-test-01
2. Complete OPNsense ISO installer (accept defaults, ZFS)
3. Assign interfaces at console prompt:
   ```
   vtnet0 → LAN
   vtnet1 → WAN1 (Proximus, future)
   vtnet2 → WAN2 (Telenet, future)
   vtnet3 → WAN3 (current internet)
   ```
4. Set LAN IP: `10.11.1.1/24`
5. Disable firewall for initial access:
   ```
   pfctl -d
   ```
6. Open WebGUI: `https://<WAN-IP>` (login: root / opnsense)
7. Create `svc-rune` user:
   ```
   WebGUI → System → Access → Users
   └── + Add
       ├── Username: svc-rune
       ├── Password: <strong password>
       ├── Group Memberships: admins
       ├── Login shell: /bin/sh    ← MANDATORY for SSH
       ├── Authorized keys: ssh-ed25519 AAAA... svc-rune@by-systems.be
       └── Save
   ```
8. Generate API key:
   ```
   WebGUI → System → Access → Users
   └── Edit svc-rune → API keys tab
       └── + (generate)
       └── Download key + secret
       └── Save to: infra/secrets/OPNsense.internal_svc-rune_apikey.txt
   ```
   File format:
   ```
   key=<API_KEY>
   secret=<API_SECRET>
   ```
9. Enable SSH:
   ```
   WebGUI → System → Settings → Administration
   └── Secure Shell section
       ├── Enable: checked
       ├── Listen interfaces: All
       └── Save
   ```
10. Verify API:
    ```bash
    curl -k -u "<key>:<secret>" https://<WAN-IP>/api/core/firmware/status
    # Expected: JSON with product_version
    ```
11. Verify SSH:
    ```bash
    ssh -i ~/.ssh/id_ed25519 svc-rune@<WAN-IP>
    # Expected: shell prompt, type 'exit'
    ```
12. Store credentials in KV format:
    ```bash
    # File: ~/.openclaw/workspace/infra/secrets/OPNsense.internal_svc-rune_apikey.txt
    key=<API_KEY>
    secret=<API_SECRET>
    host=<WAN-IP>
    port=443
    verify_ssl=false
    ```
    Then create `.env` referencing the secrets:
    ```bash
    cat > .env << 'EOF'
    OPN_HOST=<WAN-IP>
    OPN_KEY=<API_KEY>
    OPN_SECRET=<API_SECRET>
    OPN_PORT=443
    OPN_VERIFY_SSL=false
    EOF
    ```
13. Run integration tests:
    ```bash
    source .venv/bin/activate
    pytest tests/integration/ -q
    ```

## References

- [ADR-0027: OPNsense Provisioning Contract](https://github.com/by-openclaw/doc-platform-core/blob/main/docs/adr/0027-opnsense-provisioning-contract.md)
- [ADR-0032: Network Zone & VLAN Registry](https://github.com/by-openclaw/doc-platform-core/blob/main/docs/adr/0032-network-zone-vlan-registry.md)
- [ADR-0033: User Identity & Access Standard](https://github.com/by-openclaw/doc-platform-core/blob/main/docs/adr/0033-user-identity-access-standard.md)
- [docs/test-zone-plan.md](../docs/test-zone-plan.md) — full network topology and test plan
