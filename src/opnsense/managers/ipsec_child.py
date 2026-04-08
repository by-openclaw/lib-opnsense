# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec child SA manager -- CRUD + ensure().

API domain: /api/ipsec/connections
Payload key: child
Match key:   description (unique child SA description)
Entity suffix: Child (searchChild, getChild, etc.)

Endpoints:
    search  GET  ipsec/connections/searchChild
    get     GET  ipsec/connections/getChild/{uuid}
    create  POST ipsec/connections/addChild
    update  POST ipsec/connections/setChild/{uuid}
    delete  POST ipsec/connections/delChild/{uuid}
    apply   POST ipsec/service/reconfigure

Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecChildManager(BaseManager):
    """Manage OPNsense IPsec child SAs via /api/ipsec/connections.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    IPsec child SAs define phase-2 (ESP/AH) tunnel parameters.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecChildManager(client)
            result = await mgr.ensure("present", {
                "description": "lan-to-lan",
                "connection": "<parent-conn-uuid>",
                "mode": "tunnel",
            })

    Input (ensure present):
        description:    Child SA description, max 255 (required, match key)
        enabled:        Enable child SA ('0' or '1', optional, default='1')
        connection:     Parent connection UUID (optional)
        mode:           IPsec mode (optional, default='tunnel')
        policies:       Install policies ('0' or '1', optional, default='1')
        rekey_time:     Re-keying time in seconds (optional, default='3600')
        sha256_96:      SHA-256-96 compatibility ('0' or '1', optional, default='0')

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict
        after:    New state dict
    """

    _endpoint = "ipsec/connections"
    _payload_key = "child"
    _entity_suffix = "Child"
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "connection": {"type": "str"},
        "mode": {"type": "str"},
        "policies": {"type": "bool_str"},
        "rekey_time": {"type": "str"},
        "sha256_96": {"type": "bool_str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec child SA manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
