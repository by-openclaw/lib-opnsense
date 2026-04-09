# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense captive portal zone manager — CRUD + ensure().

API domain: /api/captiveportal/settings
Payload key: zone
Match key:   description (unique zone description)
Entity suffix: Zone (getZone, addZone, setZone, delZone)

Endpoints:
    search  GET  captiveportal/settings/searchZones  (plural — custom list() override)
    get     GET  captiveportal/settings/getZone/{uuid}
    create  POST captiveportal/settings/addZone
    update  POST captiveportal/settings/setZone/{uuid}
    delete  POST captiveportal/settings/delZone/{uuid}
    apply   POST captiveportal/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class CpZoneManager(BaseManager):
    """Manage OPNsense captive portal zones via /api/captiveportal/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Captive portal zones define authentication-gated network access areas.

    Note: The search endpoint uses plural form (searchZones) while
    other CRUD endpoints use singular (getZone, addZone, etc.).

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = CpZoneManager(client)
            result = await mgr.ensure("present", {
                "description": "Guest WiFi",
                "enabled": "1",
                "interfaces": "opt1",
                "idletimeout": "300",
                "hardtimeout": "3600",
            })

    Input (ensure present):
        description:      Zone description, max 255 (required)
        enabled:          Enable zone ('0' or '1', optional, default='1')
        interfaces:       Comma-separated interface names
        authservers:      Authentication server references
        idletimeout:      Idle timeout in seconds, min 0
        hardtimeout:      Hard timeout in seconds, min 0
        concurrentlogins: Allow concurrent logins ('0' or '1', optional, default='1')
        certificate:      TLS certificate UUID
        servername:       Server name for portal

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "captiveportal/settings"
    _payload_key = "zone"
    _entity_suffix = "Zone"  # getZone, addZone, setZone, delZone
    _apply_endpoint = "captiveportal/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "interfaces": {"type": "str"},
        "authservers": {"type": "str"},
        "idletimeout": {"type": "int", "min": 0},
        "hardtimeout": {"type": "int", "min": 0},
        "concurrentlogins": {"type": "bool_str"},
        "certificate": {"type": "str"},
        "servername": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the captive portal zone manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List zones — override because search endpoint uses plural (searchZones)."""
        endpoint = f"{self._endpoint}/searchZones"
        return await self._client.search(endpoint, search_phrase=search_phrase)
