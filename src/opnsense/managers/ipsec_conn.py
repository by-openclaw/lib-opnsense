# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec connection manager — CRUD + ensure().

API domain: /api/ipsec/connections
Payload key: connection
Match key:   description (unique connection description)
Entity suffix: Connection
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IpsecConnManager(BaseManager):
    """Manage OPNsense IPsec connections (tunnels)."""

    _endpoint = "ipsec/connections"
    _payload_key = "connection"
    _entity_suffix = "Connection"
    _apply_endpoint = "ipsec/service/reconfigure"
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
