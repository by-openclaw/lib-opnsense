# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec VTI manager -- CRUD + ensure().

API domain: /api/ipsec/vti
Payload key: vti
Match key:   description (unique VTI description)
Entity suffix: '' (bare: search, get, add, set, del)

Endpoints:
    search  GET  ipsec/vti/search
    get     GET  ipsec/vti/get/{uuid}
    create  POST ipsec/vti/add
    update  POST ipsec/vti/set/{uuid}
    delete  POST ipsec/vti/del/{uuid}
    apply   POST ipsec/service/reconfigure

Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecVtiManager(BaseManager):
    """Manage OPNsense IPsec VTI interfaces via /api/ipsec/vti.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    VTI (Virtual Tunnel Interface) provides route-based IPsec tunnels.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecVtiManager(client)
            result = await mgr.ensure("present", {
                "description": "vti-to-site-b",
                "reqid": "100",
                "local": "198.51.100.1",
                "remote": "203.0.113.1",
                "tunnel_local": "10.10.10.1/30",
                "tunnel_remote": "10.10.10.2/30",
            })

    Input (ensure present):
        description:    VTI description, max 255 (required, match key)
        enabled:        Enable VTI ('0' or '1', optional, default='1')
        reqid:          Request ID for policy matching (optional)
        local:          Local outer IP address (optional)
        remote:         Remote outer IP address (optional)
        tunnel_local:   Local inner tunnel address (optional)
        tunnel_remote:  Remote inner tunnel address (optional)

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict
        after:    New state dict
    """

    _endpoint = "ipsec/vti"
    _payload_key = "vti"
    _entity_suffix = ""
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "reqid": {"type": "str"},
        "local": {"type": "str"},
        "remote": {"type": "str"},
        "tunnel_local": {"type": "str"},
        "tunnel_remote": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec VTI manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
