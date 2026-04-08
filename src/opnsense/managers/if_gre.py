# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense GRE tunnel interface manager — CRUD + ensure().

API domain: /api/interfaces/gre_settings
Payload key: gre
Match keys:  ['tunnel-local-addr', 'tunnel-remote-addr']
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/gre_settings/search_item   — list GRE tunnels
    GET  /api/interfaces/gre_settings/get_item       — schema / get by UUID
    POST /api/interfaces/gre_settings/add_item       — create GRE tunnel
    POST /api/interfaces/gre_settings/set_item/{uuid} — update GRE tunnel
    POST /api/interfaces/gre_settings/del_item/{uuid} — delete GRE tunnel
    POST /api/interfaces/gre_settings/reconfigure    — apply changes

GRE fields:
    tunnel-local-addr   — local tunnel endpoint (match key)
    tunnel-remote-addr  — remote tunnel endpoint (match key)
    tunnel-remote-net   — remote network prefix length
    descr               — description

Note: API field names use hyphens (tunnel-local-addr), model uses underscores.

GRE tunnel changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfGreManager(BaseManager):
    """Manage OPNsense GRE tunnel interfaces via /api/interfaces/gre_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    GRE tunnels encapsulate arbitrary network layer protocols.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfGreManager(client)
            result = await mgr.ensure("present", {
                "tunnel-local-addr": "10.0.0.1",
                "tunnel-remote-addr": "10.0.0.2",
            })
    """

    _endpoint = "interfaces/gre_settings"
    _payload_key = "gre"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/gre_settings/reconfigure"
    _match_keys = ["tunnel-local-addr", "tunnel-remote-addr"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "tunnel-local-addr": {"type": "str", "required": True},
        "tunnel-remote-addr": {"type": "str", "required": True},
        "descr": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the GRE tunnel interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
