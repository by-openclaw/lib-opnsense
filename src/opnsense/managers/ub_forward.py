# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS forwarding manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: dot (DNS-over-TLS forward)
Match key:   domain (forward domain)
Entity suffix: Forward (search_forward, get_forward, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbForwardManager(BaseManager):
    """Manage Unbound DNS forwarding entries."""

    _endpoint = "unbound/settings"
    _payload_key = "dot"
    _entity_suffix = "Forward"
    _apply_endpoint = "unbound/service/reconfigure"
    _match_key = "domain"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
