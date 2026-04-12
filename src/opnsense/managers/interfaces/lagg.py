# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense LAGG interface manager — CRUD + ensure().

API domain: /api/interfaces/lagg_settings
Payload key: lagg
Match key:   descr (unique LAGG description)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/lagg_settings/search_item   — list LAGGs
    GET  /api/interfaces/lagg_settings/get_item       — schema / get by UUID
    POST /api/interfaces/lagg_settings/add_item       — create LAGG
    POST /api/interfaces/lagg_settings/set_item/{uuid} — update LAGG
    POST /api/interfaces/lagg_settings/del_item/{uuid} — delete LAGG
    POST /api/interfaces/lagg_settings/reconfigure    — apply changes

LAGG fields:
    descr              — description (match key)
    members            — member interfaces (comma-separated)
    proto              — aggregation protocol (lacp, failover, fec, loadbalance, none)
    lacp_fast_timeout  — LACP fast timeout ('0' or '1')
    mtu                — maximum transmission unit

LAGG changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfLaggManager(BaseManager):
    """Manage OPNsense LAGG interfaces via /api/interfaces/lagg_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    LAGG aggregates multiple physical interfaces for redundancy or throughput.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfLaggManager(client)
            result = await mgr.ensure("present", {
                "descr": "Bond0",
                "members": "vtnet1,vtnet2",
                "proto": "lacp",
            })

    Input (ensure present):
        descr:  LAGG description, max 255 (required)
        proto:  Aggregation protocol — none, lacp, failover, fec, loadbalance (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "interfaces/lagg_settings"
    _payload_key = "lagg"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/lagg_settings/reconfigure"
    _match_key = "descr"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "descr": {"type": "str", "required": True, "max_length": 255},
        "proto": {
            "type": "enum",
            "values": ["none", "lacp", "failover", "fec", "loadbalance", "roundrobin"],
        },
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the LAGG interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
