# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec pool manager -- CRUD + ensure().

API domain: /api/ipsec/pools
Payload key: pool
Match key:   name (unique pool name)
Entity suffix: '' (bare: search, get, add, set, del)

Endpoints:
    search  GET  ipsec/pools/search
    get     GET  ipsec/pools/get/{uuid}
    create  POST ipsec/pools/add
    update  POST ipsec/pools/set/{uuid}
    delete  POST ipsec/pools/del/{uuid}
    apply   POST ipsec/service/reconfigure

Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecPoolManager(BaseManager):
    """Manage OPNsense IPsec address pools via /api/ipsec/pools.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Pools define virtual IP address ranges assigned to remote peers.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecPoolManager(client)
            result = await mgr.ensure("present", {
                "name": "roadwarrior-pool",
                "addrs": "10.10.10.0/24",
            })

    Input (ensure present):
        name:       Pool name, max 255 (required, match key)
        enabled:    Enable pool ('0' or '1', optional, default='1')
        addrs:      IP pool range/CIDR (optional)
        dns:        DNS server(s) pushed to peers (optional)

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict
        after:    New state dict
    """

    _endpoint = "ipsec/pools"
    _payload_key = "pool"
    _entity_suffix = ""
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "name"

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "addrs": {"type": "str"},
        "dns": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec pool manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
