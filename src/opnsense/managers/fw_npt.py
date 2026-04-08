# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall NPTv6 (NAT66) manager -- CRUD + ensure().

API domain: /api/firewall/npt
Payload key: rule
Match keys:  ['source_net', 'destination_net']
Entity suffix: Rule (searchRule, getRule, addRule, setRule, delRule)

Endpoints:
    search  GET  firewall/npt/searchRule
    get     GET  firewall/npt/getRule/{uuid}
    create  POST firewall/npt/addRule
    update  POST firewall/npt/setRule/{uuid}
    delete  POST firewall/npt/delRule/{uuid}
    apply   POST firewall/npt/apply

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwNptManager(BaseManager):
    """Manage OPNsense NPTv6 (NAT66) rules via /api/firewall/npt.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    NPTv6 translates IPv6 network prefixes between source and destination
    networks on a specified interface.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwNptManager(client)
            result = await mgr.ensure("present", {
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
            })

    Input (ensure present):
        source_net:       Source IPv6 prefix, max 255 (required)
        destination_net:  Destination IPv6 prefix, max 255 (required)
        interface:        Interface name (required)
        enabled:          Enable rule (optional, default='1')
        log:              Log matching packets (optional, default='0')
        sequence:         Rule order priority, min 1 (optional)
        description:      Rule description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/npt"
    _payload_key = "rule"
    _entity_suffix = "Rule"  # search_rule, get_rule, add_rule, set_rule, del_rule
    _apply_endpoint = "firewall/npt/apply"
    _match_keys = ["source_net", "destination_net"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "source_net": {"type": "str", "required": True, "max_length": 255},
        "destination_net": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "enabled": {"type": "bool_str"},
        "log": {"type": "bool_str"},
        "sequence": {"type": "int", "min": 1},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall NPTv6 manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
