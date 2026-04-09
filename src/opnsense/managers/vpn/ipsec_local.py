# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec local authentication manager -- CRUD + ensure().

API domain: /api/ipsec/connections
Payload key: local
Match key:   description (unique local auth description)
Entity suffix: Local (searchLocal, getLocal, etc.)

Endpoints:
    search  GET  ipsec/connections/searchLocal
    get     GET  ipsec/connections/getLocal/{uuid}
    create  POST ipsec/connections/addLocal
    update  POST ipsec/connections/setLocal/{uuid}
    delete  POST ipsec/connections/delLocal/{uuid}
    apply   POST ipsec/service/reconfigure

Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecLocalManager(BaseManager):
    """Manage OPNsense IPsec local authentication via /api/ipsec/connections.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Local authentication defines the local identity and auth method for an
    IPsec connection.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecLocalManager(client)
            result = await mgr.ensure("present", {
                "description": "local-psk",
                "connection": "<parent-conn-uuid>",
                "auth": "psk",
            })

    Input (ensure present):
        description:    Local auth description, max 255 (required, match key)
        enabled:        Enable local auth ('0' or '1', optional, default='1')
        connection:     Parent connection UUID (optional)
        auth:           Authentication method (optional)
        id:             Local identity (optional)
        eap_id:         EAP identity (optional)
        round:          Authentication round (optional, default='0')

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict
        after:    New state dict
    """

    _endpoint = "ipsec/connections"
    _payload_key = "local"
    _entity_suffix = "Local"
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "connection": {"type": "str"},
        "auth": {"type": "str"},
        "id": {"type": "str"},
        "eap_id": {"type": "str"},
        "round": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec local authentication manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
