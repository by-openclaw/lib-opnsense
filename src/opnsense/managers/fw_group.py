# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall interface group manager — CRUD + ensure().

API domain: /api/firewall/group
Payload key: group
Match key:   ifname (unique group interface name)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Interface groups bundle multiple interfaces for rule assignment.
No reconfigure needed — groups take effect immediately.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwGroupManager(BaseManager):
    """Manage OPNsense firewall interface groups via /api/firewall/group.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Interface groups allow a single rule to apply across multiple interfaces.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwGroupManager(client)
            result = await mgr.ensure("present", {
                "ifname": "trusted",
                "members": "lan,wireguard",
                "descr": "Trusted internal interfaces",
            })
    """

    _endpoint = "firewall/group"
    _payload_key = "group"
    _entity_suffix = "Item"  # search_item, get_item, add_item, set_item, del_item
    _apply_endpoint = None  # Groups apply immediately
    _match_key = "ifname"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall interface group manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
