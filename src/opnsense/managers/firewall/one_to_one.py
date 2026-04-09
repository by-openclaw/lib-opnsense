# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall 1:1 NAT (BINAT) manager — CRUD + ensure().

API domain: /api/firewall/one_to_one
Payload key: rule
Match key:   description (unique rule description)
Entity suffix: Rule (searchRule, getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  firewall/one_to_one/searchRule
    get     GET  firewall/one_to_one/getRule/{uuid}
    create  POST firewall/one_to_one/addRule
    update  POST firewall/one_to_one/setRule/{uuid}
    delete  POST firewall/one_to_one/delRule/{uuid}
    apply   POST firewall/one_to_one/apply

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M11
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwOneToOneManager(BaseManager):
    """Manage OPNsense 1:1 NAT (BINAT) rules via /api/firewall/one_to_one.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    1:1 NAT maps an external IP bidirectionally to an internal IP.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwOneToOneManager(client)
            result = await mgr.ensure("present", {
                "description": "1:1 NAT WAN ↔ DMZ Traefik",
                "interface": "wan",
                "type": "binat",
                "external": "10.6.224.106",
                "source_net": "10.1.2.10/32",
            })

    Input (ensure present):
        description:  Rule description, max 255 (required)
        interface:    Interface name (required)
        source_net:   Source network (required)
        external:     External IP address (optional)
        disabled:     Disable rule (optional, default='0')
        sequence:     Rule order priority, min 1 (optional)
        source_not:   Invert source match (optional, default='0')
        destination_not: Invert destination match (optional, default='0')
        destination_net: Destination network (optional)
        log:          Log matching packets (optional, default='0')
        type:         NAT type — binat, nat (optional)
        natreflection: NAT reflection — '', enable, disable (optional)
        categories:   Comma-separated category UUIDs (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/one_to_one"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/one_to_one/apply"
    _match_keys = ["description", "interface", "source_net"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "source_net": {"type": "str", "required": True},
        "external": {"type": "str"},
        "disabled": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "source_not": {"type": "bool_str"},
        "destination_not": {"type": "bool_str"},
        "destination_net": {"type": "str"},
        "log": {"type": "bool_str"},
        "type": {"type": "enum", "values": ["binat", "nat"]},
        "natreflection": {"type": "enum", "values": ["", "enable", "disable"]},
        "categories": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall 1:1 NAT manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
