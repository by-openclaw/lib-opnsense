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

    Input (ensure present):
        description:  Rule description, max 255 (required)
        interface:    Interface name (required)
        source_net:   Source network (required)
        target:       NAT target address (optional)
        ipprotocol:   IP protocol — inet, inet6, inet46 (optional)
        enabled:      Enable rule (optional, default='1')
        sequence:     Rule order priority, min 1 (optional)
        source_not:   Invert source match (optional, default='0')
        destination_not: Invert destination match (optional, default='0')
        destination_port: Destination port (optional)
        source_port:  Source port (optional)
        protocol:     Protocol name (optional)
        log:          Log matching packets (optional, default='0')
        nonat:        Disable NAT (optional, default='0')
        staticnatport: Use static source port (optional, default='0')
        target_port:  Target port (optional)
        categories:   Comma-separated category UUIDs (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/source_nat"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/source_nat/apply"
    _match_keys = ["description", "interface", "source_net"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "source_net": {"type": "str", "required": True},
        "target": {"type": "str"},
        "ipprotocol": {"type": "enum", "values": ["inet", "inet6", "inet46"]},
        "enabled": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "source_not": {"type": "bool_str"},
        "destination_not": {"type": "bool_str"},
        "destination_port": {"type": "str"},
        "source_port": {"type": "str"},
        "protocol": {"type": "str"},
        "log": {"type": "bool_str"},
        "nonat": {"type": "bool_str"},
        "staticnatport": {"type": "bool_str"},
        "target_port": {"type": "str"},
        "categories": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall source NAT manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
