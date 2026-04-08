# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense traffic shaper pipe manager — CRUD + ensure().

API domain: /api/trafficshaper/settings
Payload key: pipe
Match key:   description (unique pipe description)
Entity suffix: Pipe (getPipe, addPipe, setPipe, delPipe)

Endpoints:
    search  GET  trafficshaper/settings/searchPipes  (plural — custom list() override)
    get     GET  trafficshaper/settings/getPipe/{uuid}
    create  POST trafficshaper/settings/addPipe
    update  POST trafficshaper/settings/setPipe/{uuid}
    delete  POST trafficshaper/settings/delPipe/{uuid}
    apply   POST trafficshaper/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M12
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class TsPipeManager(BaseManager):
    """Manage OPNsense traffic shaper pipes via /api/trafficshaper/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Pipes define bandwidth limits for traffic shaping.

    Note: The search endpoint uses plural form (search_pipes) while
    other CRUD endpoints use singular (get_pipe, add_pipe, etc.).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = TsPipeManager(client)
            result = await mgr.ensure("present", {
                "description": "LAN upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
                "enabled": "1",
            })
    """

    _endpoint = "trafficshaper/settings"
    _payload_key = "pipe"
    _entity_suffix = "Pipe"  # get_pipe, add_pipe, set_pipe, del_pipe
    _apply_endpoint = "trafficshaper/service/reconfigure"
    _match_keys = ["description", "bandwidth", "bandwidthMetric"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "bandwidth": {"type": "int", "required": True, "min": 1},
        "bandwidthMetric": {
            "type": "enum",
            "values": ["bit", "Kbit", "Mbit", "Gbit"],
        },
        "enabled": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the traffic shaper pipe manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List pipes — override because search endpoint uses plural (search_pipes)."""
        endpoint = f"{self._endpoint}/search_pipes"
        return await self._client.search(endpoint, search_phrase=search_phrase)
