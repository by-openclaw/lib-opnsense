# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense WireGuard server (instance) manager — CRUD + ensure().

API domain: /api/wireguard/server
Payload key: server
Match key:   name (unique instance name)
Entity suffix: Server
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class WgServerManager(BaseManager):
    """Manage OPNsense WireGuard server instances."""

    _endpoint = "wireguard/server"
    _payload_key = "server"
    _entity_suffix = "Server"
    _apply_endpoint = "wireguard/service/reconfigure"
    _match_key = "name"

    REDACT_FIELDS = {"privkey", "psk"}

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
