# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense VLAN interface manager — CRUD + ensure().

API domain: /api/interfaces/vlan_settings
Payload key: vlan
Match key:   descr (unique VLAN description)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/vlan_settings/search_item   — list VLANs
    GET  /api/interfaces/vlan_settings/get_item       — schema / get by UUID
    POST /api/interfaces/vlan_settings/add_item       — create VLAN
    POST /api/interfaces/vlan_settings/set_item/{uuid} — update VLAN
    POST /api/interfaces/vlan_settings/del_item/{uuid} — delete VLAN
    POST /api/interfaces/vlan_settings/reconfigure    — apply changes

VLAN fields:
    if      — parent interface (e.g. 'vtnet1')
    tag     — VLAN ID (e.g. '310')
    pcp     — 802.1p priority code point
    proto   — encapsulation ('', '802.1q', '802.1ad')
    descr   — description (match key)
    vlanif  — derived interface name (read-only)

VLAN changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfVlanManager(BaseManager):
    """Manage OPNsense VLAN interfaces via /api/interfaces/vlan_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    VLANs define tagged sub-interfaces on a parent NIC.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfVlanManager(client)
            result = await mgr.ensure("present", {
                "if": "vtnet1",
                "tag": "400",
                "descr": "Test VLAN",
            })

    Input (ensure present):
        tag:    VLAN ID, 1-4094 (required)
        if:     Parent interface name, e.g. 'vtnet1' (required)
        pcp:    802.1p priority code point, 0-7 (optional)
        descr:  VLAN description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "interfaces/vlan_settings"
    _payload_key = "vlan"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/vlan_settings/reconfigure"
    _match_keys = ["tag", "if"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "tag": {"type": "int", "required": True, "min": 1, "max": 4094},
        "if": {"type": "str", "required": True},
        "pcp": {"type": "int", "min": 0, "max": 7},
        "descr": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the VLAN interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
