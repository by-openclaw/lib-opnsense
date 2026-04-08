# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec connection manager -- CRUD + ensure().

API domain: /api/ipsec/connections
Payload key: connection
Match key:   description (unique connection description)
Entity suffix: Connection (searchConnection, getConnection, etc.)

Endpoints:
    search  GET  ipsec/connections/searchConnection
    get     GET  ipsec/connections/getConnection/{uuid}
    create  POST ipsec/connections/addConnection
    update  POST ipsec/connections/setConnection/{uuid}
    delete  POST ipsec/connections/delConnection/{uuid}
    apply   POST ipsec/service/reconfigure

Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecConnManager(BaseManager):
    """Manage OPNsense IPsec connections via /api/ipsec/connections.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    IPsec connections define IKE phase-1 tunnel parameters.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecConnManager(client)
            result = await mgr.ensure("present", {
                "description": "site-to-site",
                "enabled": "1",
            })

    Input (ensure present):
        description:    Connection description, max 255 (required, match key)
        enabled:        Enable connection ('0' or '1', optional, default='1')
        version:        IKE version (optional)
        aggressive:     Aggressive mode ('0' or '1', optional, default='0')
        mobike:         MOBIKE support ('0' or '1', optional, default='1')
        reauth_time:    Re-authentication time in seconds (optional)
        rekey_time:     Re-keying time in seconds (optional)
        dpd_delay:      DPD delay in seconds (optional)
        dpd_timeout:    DPD timeout in seconds (optional)
        keyingtries:    Number of keying tries (optional)

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict
        after:    New state dict
    """

    _endpoint = "ipsec/connections"
    _payload_key = "connection"
    _entity_suffix = "Connection"
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "version": {"type": "str"},
        "aggressive": {"type": "bool_str"},
        "mobike": {"type": "bool_str"},
        "reauth_time": {"type": "str"},
        "rekey_time": {"type": "str"},
        "dpd_delay": {"type": "str"},
        "dpd_timeout": {"type": "str"},
        "keyingtries": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec connection manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
