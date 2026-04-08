# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS-over-TLS manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: dot
Match keys:  ['server', 'port']
Entity suffix: Dot (searchDot, getDot, etc.)

Endpoints:
    search  GET  unbound/settings/searchDot
    get     GET  unbound/settings/getDot/{uuid}
    create  POST unbound/settings/addDot
    update  POST unbound/settings/setDot/{uuid}
    delete  POST unbound/settings/delDot/{uuid}
    apply   POST unbound/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbDotManager(BaseManager):
    """Manage OPNsense Unbound DNS-over-TLS servers via /api/unbound/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DoT servers provide encrypted DNS resolution over TLS (port 853).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbDotManager(client)
            result = await mgr.ensure("present", {
                "server": "1.1.1.1",
                "port": "853",
                "verify": "cloudflare-dns.com",
            })

    Input (ensure present):
        server:                DoT server address, max 255 (required)
        port:                  Server port (optional)
        type:                  Server type — dot (optional)
        verify:                TLS verification hostname (optional)
        forward_tcp_upstream:  Use TCP for upstream (optional, default='0')
        forward_first:         Forward first before resolving (optional, default='0')
        enabled:               Enable DoT server (optional, default='1')
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
    _entity_suffix = "Dot"
    _apply_endpoint = "unbound/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["server", "port"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "server": {"type": "str", "required": True, "max_length": 255},
        "port": {"type": "str"},
        "type": {"type": "enum", "values": ["dot"]},
        "verify": {"type": "str"},
        "forward_tcp_upstream": {"type": "bool_str"},
        "forward_first": {"type": "bool_str"},
        "enabled": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound DNS-over-TLS manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
