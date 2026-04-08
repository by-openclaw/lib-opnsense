# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Virtual IP manager — CRUD + ensure().

API domain: /api/interfaces/vip_settings
Payload key: vip
Match key:   descr (unique VIP description)
Entity suffix: Item (search_item, get_item, add_item, set_item, del_item)

Supported endpoints:
    POST /api/interfaces/vip_settings/search_item   — list VIPs
    GET  /api/interfaces/vip_settings/get_item       — schema / get by UUID
    POST /api/interfaces/vip_settings/add_item       — create VIP
    POST /api/interfaces/vip_settings/set_item/{uuid} — update VIP
    POST /api/interfaces/vip_settings/del_item/{uuid} — delete VIP
    POST /api/interfaces/vip_settings/reconfigure    — apply changes

VIP fields:
    interface — interface to bind to (e.g. 'wan', 'lan')
    mode      — VIP type: 'ipalias', 'carp', 'proxyarp', 'other'
    address   — IP address
    network   — subnet mask (CIDR bits, e.g. '32')
    descr     — description (match key)
    password  — CARP password (redacted)
    vhid      — CARP virtual host ID
    advbase   — CARP advertisement base interval
    advskew   — CARP advertisement skew

VIP changes require reconfigure to take effect.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IfVipManager(BaseManager):
    """Manage OPNsense Virtual IPs via /api/interfaces/vip_settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Virtual IPs provide additional addresses on interfaces for
    CARP failover, IP aliases, or proxy ARP.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IfVipManager(client)
            result = await mgr.ensure("present", {
                "interface": "lan",
                "mode": "ipalias",
                "address": "10.1.3.200",
                "network": "32",
                "descr": "SVC floating IP",
            })
    """

    _endpoint = "interfaces/vip_settings"
    _payload_key = "vip"
    _entity_suffix = "Item"
    _apply_endpoint = "interfaces/vip_settings/reconfigure"
    _match_keys = ["address", "interface", "mode"]

    REDACT_FIELDS = {"password"}  # CARP password

    _validators = {
        "address": {"type": "str", "required": True},
        "interface": {"type": "str", "required": True},
        "mode": {
            "type": "enum",
            "required": True,
            "values": ["ipalias", "carp", "proxyarp", "other"],
        },
        "network": {"type": "str"},
        "descr": {"type": "str", "max_length": 255},
        "password": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Virtual IP manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
