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

    Input (ensure present):
        description:      Pipe description, max 255 (required)
        bandwidth:        Bandwidth limit, min 1 (required)
        bandwidthMetric:  Bandwidth unit — bit, Kbit, Mbit, Gbit (optional)
        enabled:          Enable pipe (optional, default='1')
        delay:            Pipe delay in ms (optional)
        mask:             Mask type — none, src-ip, dst-ip, src-ip6, dst-ip6 (optional)
        buckets:          Hash buckets (optional)
        scheduler:        Scheduler — '', fifo, rr, qfq, fq_codel, fq_pie (optional)
        codel_enable:     Enable CoDel AQM (optional, default='0')
        codel_target:     CoDel target delay (optional)
        codel_interval:   CoDel interval (optional)
        codel_ecn_enable: Enable CoDel ECN (optional, default='0')
        pie_enable:       Enable PIE AQM (optional, default='0')
        fqcodel_flows:    FQ-CoDel flows (optional)
        fqcodel_limit:    FQ-CoDel limit (optional)
        fqcodel_quantum:  FQ-CoDel quantum (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
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
        "delay": {"type": "str"},
        "mask": {
            "type": "enum",
            "values": ["none", "src-ip", "dst-ip", "src-ip6", "dst-ip6"],
        },
        "buckets": {"type": "str"},
        "scheduler": {
            "type": "enum",
            "values": ["", "fifo", "rr", "qfq", "fq_codel", "fq_pie"],
        },
        "codel_enable": {"type": "bool_str"},
        "codel_target": {"type": "str"},
        "codel_interval": {"type": "str"},
        "codel_ecn_enable": {"type": "bool_str"},
        "pie_enable": {"type": "bool_str"},
        "fqcodel_flows": {"type": "str"},
        "fqcodel_limit": {"type": "str"},
        "fqcodel_quantum": {"type": "str"},
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
