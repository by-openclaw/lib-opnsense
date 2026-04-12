# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS forwarding domain manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: forward
Match keys:  ['domain', 'server']
Entity suffix: Forward (searchForward, getForward, etc.)

Endpoints:
    search  GET  unbound/settings/searchForward
    get     GET  unbound/settings/getForward/{uuid}
    create  POST unbound/settings/addForward
    update  POST unbound/settings/setForward/{uuid}
    delete  POST unbound/settings/delForward/{uuid}
    apply   POST unbound/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbForwardManager(BaseManager):
    """Manage OPNsense Unbound DNS forwarding domains via /api/unbound/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Forwarding domains route DNS queries for specific domains to upstream servers.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbForwardManager(client)
            result = await mgr.ensure("present", {
                "domain": "example.com",
                "server": "10.0.0.53",
            })

    Input (ensure present):
        domain:                Forwarding domain name, max 255 (required)
        server:                Upstream DNS server address, max 255 (optional)
        type:                  Forward type — forward, stub (optional)
        port:                  Server port (optional)
        verify:                TLS verification hostname (optional)
        forward_tcp_upstream:  Use TCP for upstream (optional, default='0')
        forward_first:         Forward first before resolving (optional, default='0')
        enabled:               Enable forward (optional, default='1')
        description:           Description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "unbound/settings"
    _payload_key = "dot"
    _entity_suffix = "Forward"
    _apply_endpoint = "unbound/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["domain", "server"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "domain": {"type": "str", "required": True, "max_length": 255},
        "server": {"type": "str", "max_length": 255},
        "type": {"type": "enum", "values": ["forward", "dot"]},
        "port": {"type": "str"},
        "verify": {"type": "str"},
        "forward_tcp_upstream": {"type": "bool_str"},
        "forward_first": {"type": "bool_str"},
        "enabled": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound forwarding domain manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
