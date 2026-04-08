# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense loopback interface manager — CRUD + ensure().

API domain: /api/interfaces/loopback_settings
Payload key: loopback
Match key:   description (unique loopback description)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/loopback_settings/search_item   — list loopbacks
    GET  /api/interfaces/loopback_settings/get_item       — schema / get by UUID
    POST /api/interfaces/loopback_settings/add_item       — create loopback
    POST /api/interfaces/loopback_settings/set_item/{uuid} — update loopback
    POST /api/interfaces/loopback_settings/del_item/{uuid} — delete loopback
    POST /api/interfaces/loopback_settings/reconfigure    — apply changes

Loopback fields:
    description — description (match key). Note: 'description' not 'descr'.
    deviceId    — device identifier (read-only)

Loopback changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfLoopbackManager(BaseManager):
    """Manage OPNsense loopback interfaces via /api/interfaces/loopback_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Loopback interfaces provide local-only network endpoints.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfLoopbackManager(client)
            result = await mgr.ensure("present", {
                "description": "Mgmt Loopback",
            })

    Input (ensure present):
        description:  Loopback description, max 255 (required)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "interfaces/loopback_settings"
    _payload_key = "loopback"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/loopback_settings/reconfigure"
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the loopback interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
