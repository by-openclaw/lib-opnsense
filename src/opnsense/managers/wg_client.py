# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense WireGuard client (peer) manager — CRUD + ensure().

API domain: /api/wireguard/client
Payload key: client
Match key:   name (unique peer name)
Entity suffix: Client
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class WgClientManager(BaseManager):
    """Manage OPNsense WireGuard client peers."""

    _endpoint = "wireguard/client"
    _payload_key = "client"
    _entity_suffix = "Client"
    _apply_endpoint = "wireguard/service/reconfigure"
    _match_key = "name"

    REDACT_FIELDS = {"psk"}  # Pre-shared key

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
