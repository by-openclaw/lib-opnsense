# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec key pair manager -- CRUD + ensure().

API domain: /api/ipsec/key_pairs
Payload key: keyPair
Match key:   name (unique key pair name)
Entity suffix: Item (searchItem, getItem, etc.)

Endpoints:
    search  GET  ipsec/key_pairs/searchItem
    get     GET  ipsec/key_pairs/getItem/{uuid}
    create  POST ipsec/key_pairs/addItem
    update  POST ipsec/key_pairs/setItem/{uuid}
    delete  POST ipsec/key_pairs/delItem/{uuid}
    apply   POST ipsec/service/reconfigure

Redact fields: privateKey
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class IpsecKeypairManager(BaseManager):
    """Manage OPNsense IPsec key pairs via /api/ipsec/key_pairs.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Key pairs store RSA/ECDSA keys for certificate-based IPsec authentication.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = IpsecKeypairManager(client)
            result = await mgr.ensure("present", {
                "name": "site-a-keypair",
                "keyType": "RSA",
            })

    Input (ensure present):
        name:           Key pair name, max 255 (required, match key)
        keyType:        Key type (optional, default='RSA')
        publicKey:      Public key PEM (optional)
        privateKey:     Private key PEM (optional, redacted in output)

    REDACT_FIELDS: privateKey -- never exposed in before/after dicts.

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "ipsec/key_pairs"
    _payload_key = "keyPair"
    _entity_suffix = "Item"
    _apply_endpoint = "ipsec/service/reconfigure"
    _apply_timeout = 30
    _match_key = "name"

    REDACT_FIELDS: set[str] = {"privateKey"}

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "keyType": {"type": "str"},
        "publicKey": {"type": "str"},
        "privateKey": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the IPsec key pair manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
