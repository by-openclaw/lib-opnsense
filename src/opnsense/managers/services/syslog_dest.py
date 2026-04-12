# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense syslog destination manager — CRUD + ensure().

API domain: /api/syslog/settings
Payload key: destination
Match key:   description (unique destination description)
Entity suffix: Destination (getDestination, addDestination, setDestination, delDestination)

Endpoints:
    search  GET  syslog/settings/searchDestinations  (plural — custom list() override)
    get     GET  syslog/settings/getDestination/{uuid}
    create  POST syslog/settings/addDestination
    update  POST syslog/settings/setDestination/{uuid}
    delete  POST syslog/settings/delDestination/{uuid}
    apply   POST syslog/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class SyslogDestManager(BaseManager):
    """Manage OPNsense syslog destinations via /api/syslog/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Syslog destinations define remote syslog targets for log forwarding.

    Note: The search endpoint uses plural form (searchDestinations) while
    other CRUD endpoints use singular (getDestination, addDestination, etc.).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = SyslogDestManager(client)
            result = await mgr.ensure("present", {
                "description": "Central syslog",
                "hostname": "syslog.example.com",
                "port": "514",
                "transport": "udp4",
                "enabled": "1",
            })

    Input (ensure present):
        description:  Destination description, max 255 (required)
        enabled:      Enable destination (optional, default='1')
        transport:    Transport — udp4, tcp4, udp6, tcp6 (optional, default='udp4')
        program:      Filter by program name (optional)
        level:        Comma-separated log levels (optional)
        facility:     Comma-separated facilities (optional)
        hostname:     Target hostname or IP, max 255 (required)
        port:         Target port number (optional, default='514')
        rfc5424:      Use RFC 5424 format (optional, default='0')
        certificate:  TLS certificate reference (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "syslog/settings"
    _payload_key = "destination"
    _entity_suffix = "Destination"  # getDestination, addDestination, etc.
    _apply_endpoint = "syslog/service/reconfigure"
    _apply_timeout = 30
    _match_keys = ["description"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "transport": {
            "type": "enum",
            "values": ["udp4", "tcp4", "udp6", "tcp6", "tls4", "tls6"],
        },
        "program": {"type": "str"},
        "level": {"type": "str"},
        "facility": {"type": "str"},
        "hostname": {"type": "str", "required": True, "max_length": 255},
        "port": {"type": "port"},
        "rfc5424": {"type": "bool_str"},
        "certificate": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the syslog destination manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List destinations — override because search endpoint uses plural (searchDestinations)."""
        endpoint = f"{self._endpoint}/searchDestinations"
        return await self._client.search(endpoint, search_phrase=search_phrase)
