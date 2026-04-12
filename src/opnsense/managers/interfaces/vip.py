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
    mode      — VIP type: 'ipalias', 'carp', 'proxyarp'
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

    Input (ensure present):
        address:    IP address (required)
        interface:  Interface to bind to, e.g. 'wan', 'lan' (required)
        mode:       VIP type — ipalias, carp, proxyarp (required)
        network:    Subnet mask in CIDR bits, e.g. '32' (optional)
        descr:      Description, max 255 (optional)
        password:   CARP password, max 255 (optional)
        advbase:    CARP advertisement base, 1-254 (optional)
        advskew:    CARP advertisement skew, 0-254 (optional)
        vhid:       CARP virtual host ID (optional)
        gateway:    Gateway IP (optional)
        nobind:     Do not bind (optional, default='0')
        noexpand:   Do not expand (optional, default='0')
        nosync:     No XMLRPC sync (optional, default='0')
        peer:       CARP peer IP (optional)
        peer6:      CARP peer IPv6 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
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
            "values": ["ipalias", "carp", "proxyarp"],
        },
        "network": {"type": "str"},
        "descr": {"type": "str", "max_length": 255},
        "password": {"type": "str", "max_length": 255},
        "advbase": {"type": "int", "min": 1, "max": 254},
        "advskew": {"type": "int", "min": 0, "max": 254},
        "vhid": {"type": "str"},
        "gateway": {"type": "str"},
        "nobind": {"type": "bool_str"},
        "noexpand": {"type": "bool_str"},
        "nosync": {"type": "bool_str"},
        "peer": {"type": "str"},
        "peer6": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Virtual IP manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
