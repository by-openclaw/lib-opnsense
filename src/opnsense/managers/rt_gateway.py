# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense routing gateway manager -- CRUD + ensure().

API domain: /api/routing/settings
Payload key: gateway_item
Match key:   name (unique gateway name)
Entity suffix: Gateway (searchGateway, getGateway, addGateway, setGateway, delGateway)

Supported endpoints:
    POST /api/routing/settings/searchGateway        -- list gateways
    GET  /api/routing/settings/getGateway            -- schema / get by UUID
    POST /api/routing/settings/addGateway            -- create gateway
    POST /api/routing/settings/setGateway/{uuid}     -- update gateway
    POST /api/routing/settings/delGateway/{uuid}     -- delete gateway
    POST /api/routing/settings/reconfigure           -- apply changes

Gateway fields:
    name         -- gateway name (match key)
    interface    -- interface name (e.g. 'wan')
    gateway      -- gateway IP address
    ipprotocol   -- 'inet' or 'inet6'
    defaultgw    -- default gateway flag ('0' or '1')
    disabled     -- disabled flag ('0' or '1')
    descr        -- description
    priority     -- priority (0-255)
    weight       -- weight (1-5)

Gateway changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class RtGatewayManager(BaseManager):
    """Manage OPNsense routing gateways via /api/routing/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Gateways define next-hop addresses for routing decisions.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = RtGatewayManager(client)
            result = await mgr.ensure("present", {
                "name": "WAN_GW",
                "interface": "wan",
                "gateway": "10.0.0.1",
            })

    Input (ensure present):
        name:        Gateway name, max 255 (required)
        interface:   Interface name, e.g. 'wan' (required)
        gateway:     Gateway IP address (required)
        ipprotocol:  IP protocol — inet, inet6 (optional)
        disabled:    Disable gateway (optional, default='0')
        defaultgw:   Default gateway flag (optional, default='0')
        priority:    Priority, 0-255 (optional)
        weight:      Weight, 1-5 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "routing/settings"
    _payload_key = "gateway_item"
    _entity_suffix = "Gateway"
    _apply_endpoint = "routing/settings/reconfigure"
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "gateway": {"type": "str", "required": True},
        "ipprotocol": {"type": "enum", "values": ["inet", "inet6"]},
        "disabled": {"type": "bool_str"},
        "defaultgw": {"type": "bool_str"},
        "priority": {"type": "int", "min": 0, "max": 255},
        "weight": {"type": "int", "min": 1, "max": 5},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the routing gateway manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
