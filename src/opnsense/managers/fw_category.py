# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall category manager — CRUD + ensure().

API domain: /api/firewall/category
Payload key: category
Match key:   name (unique category name)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Categories are labels applied to aliases and rules for grouping/filtering.
No reconfigure needed — categories take effect immediately.
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
