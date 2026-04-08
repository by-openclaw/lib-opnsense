# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall source NAT manager — CRUD + ensure() for SNAT rules.

API domain: /api/firewall/source_nat
Payload key: rule
Match key:   description (unique rule description)
Entity suffix: Rule (searchRule, getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  firewall/source_nat/searchRule
    get     GET  firewall/source_nat/getRule/{uuid}
    create  POST firewall/source_nat/addRule
    update  POST firewall/source_nat/setRule/{uuid}
    delete  POST firewall/source_nat/delRule/{uuid}
    apply   POST firewall/source_nat/apply

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M08
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwSourceNatManager(BaseManager):
    """Manage OPNsense source NAT rules via /api/firewall/source_nat.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Source NAT rules rewrite the source address of outbound traffic
    (e.g. masquerading internal networks behind a WAN IP).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwSourceNatManager(client)
            result = await mgr.ensure("present", {
                "description": "Masquerade DMZ to WAN",
                "interface": "wan",
                "source_net": "10.6.225.0/24",
                "target": "wanip",
            })
    """

    _endpoint = "firewall/source_nat"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/source_nat/apply"
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall source NAT manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
