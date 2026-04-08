# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense WireGuard server manager — CRUD + ensure().

API domain: /api/wireguard/server
Payload key: server
Match key:   name (unique server instance name)
Entity suffix: Server (searchServer, getServer, etc.)

Endpoints:
    search  GET  wireguard/server/searchServer
    get     GET  wireguard/server/getServer/{uuid}
    create  POST wireguard/server/addServer
    update  POST wireguard/server/setServer/{uuid}
    delete  POST wireguard/server/delServer/{uuid}
    apply   POST wireguard/service/reconfigure

Redact fields: privkey, pubkey
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class WgServerManager(BaseManager):
    """Manage OPNsense WireGuard server instances via /api/wireguard/server.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Server instances define local WireGuard endpoints (listen port, keys, tunnel addresses).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = WgServerManager(client)
            result = await mgr.ensure("present", {
                "name": "wg0",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
            })

    Input (ensure present):
        name:           Server name, max 255 (required)
        enabled:        Enable server ('0' or '1', optional, default='1')
        port:           Listen port 1–65535 (optional)
        mtu:            Interface MTU 68–9000 (optional)
        tunneladdress:  Tunnel addresses, comma-separated CIDRs (optional)
        dns:            DNS server(s) pushed to peers (optional)
        disableroutes:  Disable automatic route installation ('0' or '1', optional)
        gateway:        Gateway for tunnel traffic (optional)
        peers:          Comma-separated peer UUIDs (optional)

    REDACT_FIELDS: privkey, pubkey — never exposed in before/after dicts.

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "wireguard/server"
    _payload_key = "server"
    _entity_suffix = "Server"
    _apply_endpoint = "wireguard/service/reconfigure"
    _apply_timeout = 30
    _match_key = "name"

    REDACT_FIELDS: set[str] = {"privkey", "pubkey"}

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "port": {"type": "port"},
        "mtu": {"type": "int", "min": 68, "max": 9000},
        "tunneladdress": {"type": "str"},
        "dns": {"type": "str"},
        "disableroutes": {"type": "bool_str"},
        "gateway": {"type": "str"},
        "peers": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the WireGuard server manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def generate_keypair(self) -> dict[str, str]:
        """Generate a WireGuard key pair via the OPNsense API.

        Returns a dict with 'privkey' and 'pubkey'. The consumer is
        responsible for storing the private key securely (e.g. Vault KV).

        Returns:
            Dict with 'privkey' and 'pubkey' (base64-encoded).
        """
        try:
            result = await self._client.post("wireguard/server/keyPair")
            return {"privkey": result["privkey"], "pubkey": result["pubkey"]}
        except Exception as exc:
            logger.error(
                "generate_keypair failed: %s",
                exc,
                extra={"action": "generate_keypair_failed", "error": str(exc)},
            )
            raise
