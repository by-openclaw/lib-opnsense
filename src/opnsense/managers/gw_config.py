# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense gateway configuration manager — CRUD + ensure().

API domain: /api/routing/settings
Payload key: gateway_item
Match key:   name (unique gateway name)
Entity suffix: Gateway (search_gateway, get_gateway, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class GwConfigManager(BaseManager):
    """Manage OPNsense gateways."""

    _endpoint = "routing/settings"
    _payload_key = "gateway_item"
    _entity_suffix = "Gateway"
    _apply_endpoint = "routing/settings/reconfigure"
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
