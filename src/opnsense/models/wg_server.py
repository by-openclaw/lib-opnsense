# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense WireGuard server model — typed frozen dataclass.

Maps to OPNsense API: ``/api/wireguard/server``
Payload key: ``server``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WgServer:
    """WireGuard server (local peer) entity from OPNsense wireguard/server API.

    Attributes:
        name:           Server instance name (required).
        enabled:        Whether the server is enabled ('0' or '1').
        port:           Listen port.
        mtu:            Interface MTU (68–9000).
        tunneladdress:  Tunnel addresses (comma-separated CIDRs).
        dns:            DNS server(s) pushed to peers.
        disableroutes:  Disable automatic route installation ('0' or '1').
        gateway:        Gateway for tunnel traffic.
        privkey:        Private key (redacted in output).
        pubkey:         Public key (redacted in output).
        peers:          Comma-separated peer UUIDs.
        uuid:           Resource UUID assigned by OPNsense.
    """

    name: str
    enabled: str = "1"
    port: str = ""
    mtu: str = ""
    tunneladdress: str = ""
    dns: str = ""
    disableroutes: str = "0"
    gateway: str = ""
    privkey: str = ""
    pubkey: str = ""
    peers: str = ""
    uuid: str = ""
