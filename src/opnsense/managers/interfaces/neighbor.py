# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense neighbor (ARP/NDP) manager — CRUD + ensure().

API domain: /api/interfaces/neighbor_settings
Payload key: neighbor
Match keys:  ['ipaddress', 'etheraddr']
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/neighbor_settings/search_item   — list neighbors
    GET  /api/interfaces/neighbor_settings/get_item       — schema / get by UUID
    POST /api/interfaces/neighbor_settings/add_item       — create neighbor
    POST /api/interfaces/neighbor_settings/set_item/{uuid} — update neighbor
    POST /api/interfaces/neighbor_settings/del_item/{uuid} — delete neighbor
    POST /api/interfaces/neighbor_settings/reconfigure    — apply changes

Neighbor fields:
    ipaddress  — IP address (match key)
    etheraddr  — MAC / Ethernet address (match key)
    descr      — description

Neighbor changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfNeighborManager(BaseManager):
    """Manage OPNsense neighbor entries via /api/interfaces/neighbor_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Neighbor entries define static ARP/NDP mappings.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfNeighborManager(client)
            result = await mgr.ensure("present", {
                "ipaddress": "10.0.0.1",
                "etheraddr": "00:11:22:33:44:55",
            })

    Input (ensure present):
        ipaddress:  IP address (required)
        etheraddr:  MAC / Ethernet address (required)
        descr:      Description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "interfaces/neighbor_settings"
    _payload_key = "neighbor"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/neighbor_settings/reconfigure"
    _match_keys = ["ipaddress", "etheraddr"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "ipaddress": {"type": "str", "required": True},
        "etheraddr": {"type": "str", "required": True},
        "descr": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the neighbor manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
