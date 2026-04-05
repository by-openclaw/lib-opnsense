# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall filter rule manager — CRUD + ensure() for filter rules.

API domain: /api/firewall/filter
Payload key: rule
Match key:   description (unique rule description)
Entity suffix: Rule (search_rule, get_rule, add_rule, set_rule, del_rule)

Filter rule changes require apply to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwFilterManager(BaseManager):
    """Manage OPNsense firewall filter rules via /api/firewall/filter.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Filter rules control traffic flow (pass/block/reject) per interface,
    protocol, source/destination, and direction.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwFilterManager(client)
            result = await mgr.ensure("present", {
                "description": "Allow HTTPS from DMZ",
                "action": "pass",
                "interface": "lan",
                "direction": "in",
                "protocol": "TCP",
                "destination_port": "443",
            })
    """

    _endpoint = "firewall/filter"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/filter/apply"
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall filter rule manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
