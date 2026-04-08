# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense routing route manager -- CRUD + ensure().

API domain: /api/routes/routes
Payload key: route
Match keys:  ['network', 'gateway'] (composite)
Entity suffix: Route (searchRoute, getRoute, addRoute, setRoute, delRoute)

Supported endpoints:
    POST /api/routes/routes/searchRoute        -- list routes
    GET  /api/routes/routes/getRoute            -- schema / get by UUID
    POST /api/routes/routes/addRoute            -- create route
    POST /api/routes/routes/setRoute/{uuid}     -- update route
    POST /api/routes/routes/delRoute/{uuid}     -- delete route
    POST /api/routes/routes/reconfigure         -- apply changes

Route fields:
    network   -- destination network (e.g. '10.99.0.0/24')
    gateway   -- gateway UUID or name
    descr     -- description (max 255)
    disabled  -- disabled flag ('0' or '1')

Route changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class RtRouteManager(BaseManager):
    """Manage OPNsense static routes via /api/routes/routes.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Routes define static routing table entries.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = RtRouteManager(client)
            result = await mgr.ensure("present", {
                "network": "10.99.0.0/24",
                "gateway": "WAN_DHCP",
                "descr": "Test route",
                "disabled": "1",
            })

    Input (ensure present):
        network:   Destination network CIDR, e.g. '10.99.0.0/24' (required)
        gateway:   Gateway UUID or name (required)
        descr:     Description, max 255 (optional)
        disabled:  Disable route (optional, default='0')

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "routes/routes"
    _payload_key = "route"
    _entity_suffix = "Route"
    _apply_endpoint = "routes/routes/reconfigure"
    _match_keys = ["network", "gateway"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "network": {"type": "str", "required": True},
        "gateway": {"type": "str", "required": True},
        "descr": {"type": "str", "max_length": 255},
        "disabled": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the routing route manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
