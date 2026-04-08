# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense GIF tunnel interface manager — CRUD + ensure().

API domain: /api/interfaces/gif_settings
Payload key: gif
Match keys:  ['tunnel-local-addr', 'tunnel-remote-addr']
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/gif_settings/search_item   — list GIF tunnels
    GET  /api/interfaces/gif_settings/get_item       — schema / get by UUID
    POST /api/interfaces/gif_settings/add_item       — create GIF tunnel
    POST /api/interfaces/gif_settings/set_item/{uuid} — update GIF tunnel
    POST /api/interfaces/gif_settings/del_item/{uuid} — delete GIF tunnel
    POST /api/interfaces/gif_settings/reconfigure    — apply changes

GIF fields:
    tunnel-local-addr   — local tunnel endpoint (match key)
    tunnel-remote-addr  — remote tunnel endpoint (match key)
    tunnel-remote-net   — remote network prefix length
    descr               — description

Note: API field names use hyphens (tunnel-local-addr), model uses underscores.

GIF tunnel changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfGifManager(BaseManager):
    """Manage OPNsense GIF tunnel interfaces via /api/interfaces/gif_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    GIF tunnels encapsulate IPv4/IPv6 traffic in generic tunnel interfaces.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfGifManager(client)
            result = await mgr.ensure("present", {
                "tunnel-local-addr": "10.0.0.1",
                "tunnel-remote-addr": "10.0.0.2",
            })

    Input (ensure present):
        tunnel-local-addr:   Local tunnel endpoint IP (required)
        tunnel-remote-addr:  Remote tunnel endpoint IP (required)
        descr:               Description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "interfaces/gif_settings"
    _payload_key = "gif"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/gif_settings/reconfigure"
    _match_keys = ["tunnel-local-addr", "tunnel-remote-addr"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "tunnel-local-addr": {"type": "str", "required": True},
        "tunnel-remote-addr": {"type": "str", "required": True},
        "descr": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the GIF tunnel interface manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
