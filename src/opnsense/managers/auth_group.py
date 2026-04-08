# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth group manager — CRUD + ensure() for local groups.

API domain: /api/auth/group
Payload key: group
Match key:   name (unique group name)
Entity suffix: '' (bare: search, get, add, set, del)

Endpoints:
    search  GET  auth/group/search
    get     GET  auth/group/get/{uuid}
    create  POST auth/group/add
    update  POST auth/group/set/{uuid}
    delete  POST auth/group/del/{uuid}
    apply   None — auth changes apply immediately

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M02
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

    Input (ensure present):
        name:         Group name, alphanumeric/underscore/hyphen, max 32 (required)
        description:  Group description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "auth/group"
    _payload_key = "group"
    _entity_suffix = ""  # auth/group uses bare names: search, get, add, set, del
    _apply_endpoint = None  # Auth changes apply immediately
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 32, "regex": r"^[a-zA-Z0-9_\-]+$"},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the auth group manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
