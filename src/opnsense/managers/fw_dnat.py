# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall D-NAT (port forward) manager — CRUD + ensure().

API domain: /api/firewall/d_nat
Payload key: rule
Match key:   descr (unique rule description — note: 'descr' not 'description')
Entity suffix: Rule (searchRule, getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  firewall/d_nat/searchRule
    get     GET  firewall/d_nat/getRule/{uuid}
    create  POST firewall/d_nat/addRule
    update  POST firewall/d_nat/setRule/{uuid}
    delete  POST firewall/d_nat/delRule/{uuid}
    apply   POST firewall/d_nat/apply

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M07

.. note::
    D-NAT was migrated from legacy PHP to MVC in OPNsense **26.1**.
    This manager requires OPNsense >= 26.1.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwDnatManager(BaseManager):
    """Manage OPNsense D-NAT / port forward rules via /api/firewall/d_nat.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    D-NAT rules redirect inbound traffic to internal hosts (port forwarding).

    Requires OPNsense >= 26.1 (legacy PHP before that — no API).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwDnatManager(client)
            result = await mgr.ensure("present", {
                "descr": "Forward HTTPS to web server",
                "interface": "wan",
                "protocol": "tcp",
                "destination": {"network": "wanip", "port": "443"},
                "target": "10.6.225.10",
                "local-port": "443",
            })

    Input (ensure present):
        descr:       Rule description, max 255 (required)
        interface:   Interface name (required)
        target:      Destination IP address for forwarding (required)
        local-port:  Local port to forward to (optional)
        protocol:    Protocol name (optional)
        ipprotocol:  IP protocol — inet, inet6, inet46 (optional)
        disabled:    Disable rule (optional, default='0')
        sequence:    Rule order priority, min 1 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/d_nat"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/d_nat/apply"
    _match_keys = ["descr", "interface", "target"]  # D-NAT uses 'descr' not 'description'

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "descr": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "target": {"type": "ip", "required": True},
        "local-port": {"type": "port"},
        "protocol": {"type": "str"},
        "ipprotocol": {"type": "enum", "values": ["inet", "inet6", "inet46"]},
        "disabled": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "log": {"type": "bool_str"},
        "nordr": {"type": "bool_str"},
        "nosync": {"type": "bool_str"},
        "natreflection": {"type": "enum", "values": ["", "purenat", "disable"]},
        "tag": {"type": "str"},
        "tagged": {"type": "str"},
        "source": {
            "type": "dict",
            "fields": {
                "network": {"type": "str"},
                "address": {"type": "str"},
                "port": {"type": "str"},
                "not": {"type": "bool_str"},
            },
        },
        "destination": {
            "type": "dict",
            "fields": {
                "network": {"type": "str"},
                "address": {"type": "str"},
                "port": {"type": "str"},
                "not": {"type": "bool_str"},
            },
        },
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall D-NAT manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
