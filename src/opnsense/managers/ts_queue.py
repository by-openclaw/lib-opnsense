# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense traffic shaper queue manager — CRUD + ensure().

API domain: /api/trafficshaper/settings
Payload key: queue
Match key:   description (unique queue description)
Entity suffix: Queue (getQueue, addQueue, setQueue, delQueue)

Endpoints:
    search  GET  trafficshaper/settings/searchQueues  (plural — custom list() override)
    get     GET  trafficshaper/settings/getQueue/{uuid}
    create  POST trafficshaper/settings/addQueue
    update  POST trafficshaper/settings/setQueue/{uuid}
    delete  POST trafficshaper/settings/delQueue/{uuid}
    apply   POST trafficshaper/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M13
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class TsQueueManager(BaseManager):
    """Manage OPNsense traffic shaper queues via /api/trafficshaper/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Queues define weighted fair queueing for traffic shaping.

    Note: The search endpoint uses plural form (searchQueues) while
    other CRUD endpoints use singular (getQueue, addQueue, etc.).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = TsQueueManager(client)
            result = await mgr.ensure("present", {
                "description": "VoIP priority",
                "weight": "90",
                "enabled": "1",
            })
    """

    _endpoint = "trafficshaper/settings"
    _payload_key = "queue"
    _entity_suffix = "Queue"  # getQueue, addQueue, setQueue, delQueue
    _apply_endpoint = "trafficshaper/service/reconfigure"
    _match_keys = ["description"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "weight": {"type": "int", "min": 1, "max": 100},
        "enabled": {"type": "bool_str"},
        "mask": {
            "type": "enum",
            "values": ["none", "src-ip", "dst-ip", "src-ip6", "dst-ip6"],
        },
        "codel_enable": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the traffic shaper queue manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List queues — override because search endpoint uses plural (searchQueues)."""
        endpoint = f"{self._endpoint}/searchQueues"
        return await self._client.search(endpoint, search_phrase=search_phrase)
