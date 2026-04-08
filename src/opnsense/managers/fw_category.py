# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall category manager — CRUD + ensure().

API domain: /api/firewall/category
Payload key: category
Match key:   name (unique category name)
Entity suffix: Item (searchItem, getItem, addItem, setItem, delItem)

Endpoints:
    search  GET  firewall/category/searchItem
    get     GET  firewall/category/getItem/{uuid}
    create  POST firewall/category/addItem
    update  POST firewall/category/setItem/{uuid}
    delete  POST firewall/category/delItem/{uuid}
    apply   None — categories apply immediately

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M09
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwCategoryManager(BaseManager):
    """Manage OPNsense firewall categories via /api/firewall/category.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Categories label aliases and rules for filtering in the WebGUI and API.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwCategoryManager(client)
            result = await mgr.ensure("present", {
                "name": "infrastructure",
                "color": "#0000ff",
            })
    """

    _endpoint = "firewall/category"
    _payload_key = "category"
    _entity_suffix = "Item"  # search_item, get_item, add_item, set_item, del_item
    _apply_endpoint = None  # Categories apply immediately
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall category manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
