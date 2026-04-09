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

    Input (ensure present):
        description:      Rule description, max 255 (required)
        interface:        Network interface (required)
        proto:            Protocol — ip, ip4, ip6, udp, tcp (optional)
        direction:        Traffic direction — '', in, out (optional)
        enabled:          Enable rule (optional, default='1')
        sequence:         Rule priority / sequence number, min 1 (optional)
        src_port:         Source port filter (optional)
        dst_port:         Destination port filter (optional)
        source_not:       Invert source match (optional, default='0')
        destination_not:  Invert destination match (optional, default='0')
        dscp:             DSCP marking (optional)
        iplen:            IP length match (optional)
        interface2:       Second interface (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
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
        "src_port": {"type": "port_or_alias"},
        "dst_port": {"type": "port_or_alias"},
        "source_not": {"type": "bool_str"},
        "destination_not": {"type": "bool_str"},
        "dscp": {"type": "str"},
        "iplen": {"type": "str"},
        "interface2": {"type": "str"},
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
