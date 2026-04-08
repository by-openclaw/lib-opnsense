# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense WireGuard client (peer) model — typed frozen dataclass.

Maps to OPNsense API: ``/api/wireguard/client``
Payload key: ``client``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WgClient:
    """WireGuard client (remote peer) entity from OPNsense wireguard/client API.

    Attributes:
        name:           Peer name (required).
        enabled:        Whether the peer is enabled ('0' or '1').
        pubkey:         Peer's public key (redacted in output).
        psk:            Pre-shared key (redacted in output).
        tunneladdress:  Allowed IPs (comma-separated CIDRs).
        serveraddress:  Remote endpoint IP or hostname.
        serverport:     Remote endpoint port.
        keepalive:      Persistent keepalive interval in seconds.
        uuid:           Resource UUID assigned by OPNsense.
    """

    name: str
    enabled: str = "1"
    pubkey: str = ""
    psk: str = ""
    tunneladdress: str = ""
    serveraddress: str = ""
    serverport: str = ""
    keepalive: str = ""
    uuid: str = ""
