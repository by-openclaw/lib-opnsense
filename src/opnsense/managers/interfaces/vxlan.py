# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense VXLAN interface manager — CRUD + ensure().

API domain: /api/interfaces/vxlan_settings
Payload key: vxlan
Match keys:  ['vxlanid', 'vxlanlocal']
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/vxlan_settings/search_item   — list VXLANs
    GET  /api/interfaces/vxlan_settings/get_item       — schema / get by UUID
    POST /api/interfaces/vxlan_settings/add_item       — create VXLAN
    POST /api/interfaces/vxlan_settings/set_item/{uuid} — update VXLAN
    POST /api/interfaces/vxlan_settings/del_item/{uuid} — delete VXLAN
    POST /api/interfaces/vxlan_settings/reconfigure    — apply changes

VXLAN fields:
    vxlanid         — VXLAN Network Identifier (1-16777215, match key)
    vxlanlocal      — local VTEP address (match key)
    vxlanlocalport  — local UDP port
    vxlanremote     — remote VTEP address
    vxlanremoteport — remote UDP port

VXLAN changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfVxlanManager(BaseManager):
    """Manage OPNsense VXLAN interfaces via /api/interfaces/vxlan_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    VXLANs provide Layer 2 overlay networks over Layer 3 infrastructure.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfVxlanManager(client)
            result = await mgr.ensure("present", {
                "vxlanid": "100",
                "vxlanlocal": "10.0.0.1",
            })

    Input (ensure present):
        vxlanid:     VXLAN Network Identifier, 1-16777215 (required)
        vxlanlocal:  Local VTEP address (required)
        vxlanremote: Remote VTEP address (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "interfaces/vxlan_settings"
    _payload_key = "vxlan"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/vxlan_settings/reconfigure"
    _match_keys = ["vxlanid", "vxlanlocal"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "vxlanid": {"type": "int", "required": True, "min": 1, "max": 16777215},
        "vxlanlocal": {"type": "str", "required": True},
        "vxlanremote": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the VXLAN interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
