# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS host override manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: host
Match key:   hostname (unique hostname)
Entity suffix: HostOverride (search_host_override, get_host_override, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbHostOverrideManager(BaseManager):
    """Manage Unbound DNS host overrides (local A/AAAA/MX records)."""

    _endpoint = "unbound/settings"
    _payload_key = "host"
    _entity_suffix = "HostOverride"
    _apply_endpoint = "unbound/service/reconfigure"
    _match_key = "hostname"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
