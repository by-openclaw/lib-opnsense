# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall alias manager — CRUD + ensure() for aliases.

API domain: /api/firewall/alias
Payload key: alias
Match key:   name (unique alias name)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Alias changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwAliasManager(BaseManager):
    """Manage OPNsense firewall aliases via /api/firewall/alias.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Aliases reference hosts, networks, ports, URLs, GeoIP, etc.
    Redacts password/username fields used for URL table authentication.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwAliasManager(client)
            result = await mgr.ensure("present", {
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24",
                "description": "DMZ subnet",
            })
    """

    _endpoint = "firewall/alias"
    _payload_key = "alias"
    _entity_suffix = "Item"  # search_item, get_item, add_item, set_item, del_item
    _apply_endpoint = "firewall/alias/reconfigure"
    _match_key = "name"

    REDACT_FIELDS = {"password", "username"}

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall alias manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
