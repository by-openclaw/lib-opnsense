# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense WireGuard client (peer) manager — CRUD + ensure().

API domain: /api/wireguard/client
Payload key: client
Match key:   name (unique peer name)
Entity suffix: Client (searchClient, getClient, etc.)

Endpoints:
    search  GET  wireguard/client/searchClient
    get     GET  wireguard/client/getClient/{uuid}
    create  POST wireguard/client/addClient
    update  POST wireguard/client/setClient/{uuid}
    delete  POST wireguard/client/delClient/{uuid}
    apply   POST wireguard/service/reconfigure

Redact fields: psk, pubkey
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class WgClientManager(BaseManager):
    """Manage OPNsense WireGuard clients (peers) via /api/wireguard/client.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Clients define remote WireGuard peers (public key, endpoint, allowed IPs).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = WgClientManager(client)
            result = await mgr.ensure("present", {
                "name": "peer-remote",
                "pubkey": "abc123...",
                "tunneladdress": "10.10.0.2/32",
                "serveraddress": "vpn.example.com",
                "serverport": "51820",
            })

    Input (ensure present):
        name:           Peer name, max 255 (required)
        enabled:        Enable peer ('0' or '1', optional, default='1')
        pubkey:         Peer's public key (optional)
        psk:            Pre-shared key (optional)
        tunneladdress:  Allowed IPs, comma-separated CIDRs (optional)
        serveraddress:  Remote endpoint IP or hostname (optional)
        serverport:     Remote endpoint port 1–65535 (optional)
        keepalive:      Persistent keepalive interval, 0+ seconds (optional)

    REDACT_FIELDS: psk, pubkey — never exposed in before/after dicts.

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "wireguard/client"
    _payload_key = "client"
    _entity_suffix = "Client"
    _apply_endpoint = "wireguard/service/reconfigure"
    _apply_timeout = 30
    _match_key = "name"

    REDACT_FIELDS: set[str] = {"psk", "pubkey"}

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "pubkey": {"type": "str"},
        "psk": {"type": "str"},
        "tunneladdress": {"type": "str"},
        "serveraddress": {"type": "str"},
        "serverport": {"type": "port"},
        "keepalive": {"type": "int", "min": 0},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the WireGuard client manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
