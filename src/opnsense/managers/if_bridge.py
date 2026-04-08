# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense bridge interface manager — CRUD + ensure().

API domain: /api/interfaces/bridge_settings
Payload key: bridge
Match key:   descr (unique bridge description)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/bridge_settings/search_item   — list bridges
    GET  /api/interfaces/bridge_settings/get_item       — schema / get by UUID
    POST /api/interfaces/bridge_settings/add_item       — create bridge
    POST /api/interfaces/bridge_settings/set_item/{uuid} — update bridge
    POST /api/interfaces/bridge_settings/del_item/{uuid} — delete bridge
    POST /api/interfaces/bridge_settings/reconfigure    — apply changes

Bridge fields:
    descr      — description (match key)
    members    — member interfaces (comma-separated)
    linklocal  — link-local address ('0' or '1')
    enablestp  — enable STP ('0' or '1')
    proto      — STP protocol ('rstp', 'stp')

Bridge changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfBridgeManager(BaseManager):
    """Manage OPNsense bridge interfaces via /api/interfaces/bridge_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Bridges aggregate multiple interfaces into a single broadcast domain.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfBridgeManager(client)
            result = await mgr.ensure("present", {
                "descr": "LAN Bridge",
                "members": "vtnet1,vtnet2",
            })
    """

    _endpoint = "interfaces/bridge_settings"
    _payload_key = "bridge"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/bridge_settings/reconfigure"
    _match_key = "descr"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "descr": {"type": "str", "required": True, "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the bridge interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
