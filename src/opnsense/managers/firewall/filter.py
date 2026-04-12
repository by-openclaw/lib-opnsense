# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall filter rule manager — CRUD + ensure() for filter rules.

API domain: /api/firewall/filter
Payload key: rule
Match key:   description (unique rule description)
Entity suffix: Rule (searchRule, getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  firewall/filter/searchRule
    get     GET  firewall/filter/getRule/{uuid}
    create  POST firewall/filter/addRule
    update  POST firewall/filter/setRule/{uuid}
    delete  POST firewall/filter/delRule/{uuid}
    apply   POST firewall/filter/apply

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M06
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

    Input (ensure present):
        description:      Rule description, max 255 (required)
        action:           Rule action — pass, block, reject (required)
        interface:        Interface name (required)
        direction:        Traffic direction — in, out, any (optional)
        protocol:         Protocol name (optional)
        ipprotocol:       IP protocol — inet, inet6, inet46 (optional)
        source_net:       Source network, max 255 (optional)
        destination_net:  Destination network, max 255 (optional)
        source_port:      Source port, max 255 (optional)
        destination_port: Destination port, max 255 (optional)
        enabled:          Enable rule (optional, default='1')
        log:              Log matching packets (optional, default='0')
        quick:            Quick match (optional, default='1')
        sequence:         Rule order priority, min 1 (optional)
        source_not:       Invert source match (optional, default='0')
        destination_not:  Invert destination match (optional, default='0')
        interfacenot:     Invert interface match (optional, default='0')
        gateway:          Policy routing gateway (optional)
        categories:       Comma-separated category UUIDs (optional)
        icmptype:         ICMP types, comma-separated (optional)
        icmp6type:        ICMPv6 types, comma-separated (optional)
        statetype:        State type — keep, sloppy, modulate, synproxy, none (optional)
        tag:              PF tag to apply (optional)
        tagged:           Match PF tag (optional)
        nosync:           No XML sync (optional, default='0')

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/filter"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/filter/apply"
    _match_keys = ["description", "interface", "direction", "protocol"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "action": {"type": "enum", "required": True, "values": ["pass", "block", "reject"]},
        "interface": {"type": "str", "required": True},
        "direction": {"type": "enum", "values": ["in", "out", "any"]},
        "protocol": {"type": "str"},
        "ipprotocol": {"type": "enum", "values": ["inet", "inet6", "inet46"]},
        "source_net": {"type": "str", "max_length": 255},
        "destination_net": {"type": "str", "max_length": 255},
        "source_port": {"type": "str", "max_length": 255},
        "destination_port": {"type": "str", "max_length": 255},
        "enabled": {"type": "bool_str"},
        "log": {"type": "bool_str"},
        "quick": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "source_not": {"type": "bool_str"},
        "destination_not": {"type": "bool_str"},
        "interfacenot": {"type": "bool_str"},
        "gateway": {"type": "str"},
        "categories": {"type": "str"},
        "icmptype": {"type": "str"},
        "icmp6type": {"type": "str"},
        "statetype": {"type": "enum", "values": ["keep", "sloppy", "modulate", "synproxy", "none"]},
        "tag": {"type": "str"},
        "tagged": {"type": "str"},
        "nosync": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall filter rule manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
