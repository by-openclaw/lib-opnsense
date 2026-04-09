# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec pre-shared key manager -- CRUD + ensure().

API domain: /api/ipsec/pre_shared_keys
Payload key: preSharedKey
Match key:   description (unique PSK description)
Entity suffix: Item (searchItem, getItem, etc.)

Endpoints:
    search  GET  ipsec/pre_shared_keys/searchItem
    get     GET  ipsec/pre_shared_keys/getItem/{uuid}
    create  POST ipsec/pre_shared_keys/addItem
    update  POST ipsec/pre_shared_keys/setItem/{uuid}
    delete  POST ipsec/pre_shared_keys/delItem/{uuid}
    apply   POST ipsec/service/reconfigure

Redact fields: Key
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecPskManager(BaseManager):
    """Manage OPNsense IPsec pre-shared keys via /api/ipsec/pre_shared_keys.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Pre-shared keys are used for IKE authentication.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecPskManager(client)
            result = await mgr.ensure("present", {
                "description": "site-a-psk",
                "ident": "site-a.example.com",
                "Key": "supersecret",
            })

    Input (ensure present):
        description:    PSK description, max 255 (required, match key)
        ident:          Local identity (optional)
        remote_ident:   Remote identity (optional)
        keyType:        Key type (optional, default='PSK')
        Key:            Pre-shared key value (optional, redacted in output)

    REDACT_FIELDS: Key -- never exposed in before/after dicts.

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "ipsec/pre_shared_keys"
    _payload_key = "preSharedKey"
    _entity_suffix = "Item"
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    REDACT_FIELDS: set[str] = {"Key"}

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "ident": {"type": "str"},
        "remote_ident": {"type": "str"},
        "keyType": {"type": "str"},
        "Key": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec pre-shared key manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
