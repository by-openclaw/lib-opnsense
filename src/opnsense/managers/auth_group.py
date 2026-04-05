# Copyright (c) 2026 BY-SYSTEMS. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth group manager — CRUD + ensure() for local groups.

API domain: /api/auth/group
Payload key: group
Match key:   name (unique group name)

Auth changes apply immediately — no reconfigure endpoint needed.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class AuthGroupManager(BaseManager):
    """Manage OPNsense local groups via /api/auth/group.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    No sensitive fields to redact for groups.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = AuthGroupManager(client)
            result = await mgr.ensure("present", {"name": "admins", "description": "..."})
    """

    _endpoint = "auth/group"
    _payload_key = "group"
    _apply_endpoint = None  # Auth changes apply immediately
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the auth group manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
