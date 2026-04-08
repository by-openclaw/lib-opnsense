# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall interface group manager — CRUD + ensure().

API domain: /api/firewall/group
Payload key: group
Match key:   ifname (unique group interface name)
Entity suffix: Item (searchItem, getItem, addItem, setItem, delItem)

Endpoints:
    search  GET  firewall/group/searchItem
    get     GET  firewall/group/getItem/{uuid}
    create  POST firewall/group/addItem
    update  POST firewall/group/setItem/{uuid}
    delete  POST firewall/group/delItem/{uuid}
    apply   None — groups apply immediately

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M10
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

    Input (ensure present):
        ifname:    Interface group name, alphanumeric/underscore, max 32 (required)
        members:   Member interfaces, comma-separated (required)
        descr:     Description, max 255 (optional)
        sequence:  Group order priority, min 1 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/group"
    _payload_key = "group"
    _entity_suffix = "Item"  # search_item, get_item, add_item, set_item, del_item
    _apply_endpoint = None  # Groups apply immediately
    _match_key = "ifname"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "ifname": {"type": "str", "required": True, "max_length": 32, "regex": r"^[a-zA-Z0-9_]+$"},
        "members": {"type": "str", "required": True},
        "descr": {"type": "str", "max_length": 255},
        "sequence": {"type": "int", "min": 1},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall interface group manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
