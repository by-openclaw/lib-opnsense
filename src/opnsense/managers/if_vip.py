# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Virtual IP manager — CRUD + ensure().

API domain: /api/interfaces/vip_settings
Payload key: vip
Match key:   descr (unique VIP description)
Entity suffix: Item
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfVipManager(BaseManager):
    """Manage OPNsense Virtual IPs (CARP, IP Alias, etc.)."""

    _endpoint = "interfaces/vip_settings"
    _payload_key = "vip"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/vip_settings/reconfigure"
    _match_key = "descr"

    REDACT_FIELDS = {"password"}  # CARP password

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
