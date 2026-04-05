# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense static route manager — CRUD + ensure().

API domain: /api/routes/routes
Payload key: route
Match key:   descr (unique route description)
Entity suffix: Route (searchroute, getroute, addroute, setroute, delroute)

Note: Route endpoints use lowercase without underscore (searchroute not search_route).
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class RtRouteManager(BaseManager):
    """Manage OPNsense static routes."""

    _endpoint = "routes/routes"
    _payload_key = "route"
    _entity_suffix = "route"  # lowercase: searchroute, getroute, addroute
    _apply_endpoint = "routes/routes/reconfigure"
    _match_key = "descr"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
