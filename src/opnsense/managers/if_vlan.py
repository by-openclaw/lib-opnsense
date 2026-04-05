# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense VLAN interface manager — CRUD + ensure().

API domain: /api/interfaces/vlan_settings
Payload key: vlan
Match key:   descr (unique VLAN description)
Entity suffix: Item
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfVlanManager(BaseManager):
    """Manage OPNsense VLAN interfaces via /api/interfaces/vlan_settings."""

    _endpoint = "interfaces/vlan_settings"
    _payload_key = "vlan"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/vlan_settings/reconfigure"
    _match_key = "descr"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
