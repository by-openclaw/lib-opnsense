# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense traffic shaper rule manager — CRUD + ensure().

API domain: /api/trafficshaper/settings
Payload key: rule
Match keys:  ['description', 'interface', 'proto']
Entity suffix: Rule (getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  trafficshaper/settings/searchRules  (plural — custom list() override)
    get     GET  trafficshaper/settings/getRule/{uuid}
    create  POST trafficshaper/settings/addRule
    update  POST trafficshaper/settings/setRule/{uuid}
    delete  POST trafficshaper/settings/delRule/{uuid}
    apply   POST trafficshaper/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M14
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class TsRuleManager(BaseManager):
    """Manage OPNsense traffic shaper rules via /api/trafficshaper/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Rules bind traffic to pipes/queues based on interface, protocol, and direction.

    Note: The search endpoint uses plural form (searchRules) while
    other CRUD endpoints use singular (getRule, addRule, etc.).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = TsRuleManager(client)
            result = await mgr.ensure("present", {
                "description": "Shape VoIP",
                "interface": "lan",
                "proto": "udp",
                "direction": "in",
                "enabled": "1",
            })
    """

    _endpoint = "trafficshaper/settings"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # getRule, addRule, setRule, delRule
    _apply_endpoint = "trafficshaper/service/reconfigure"
    _match_keys = ["description", "interface", "proto"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "proto": {
            "type": "enum",
            "values": ["ip", "ip4", "ip6", "udp", "tcp"],
        },
        "direction": {"type": "enum", "values": ["", "in", "out"]},
        "enabled": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "src_port": {"type": "str"},
        "dst_port": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the traffic shaper rule manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List rules — override because search endpoint uses plural (searchRules)."""
        endpoint = f"{self._endpoint}/searchRules"
        return await self._client.search(endpoint, search_phrase=search_phrase)
