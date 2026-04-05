# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec pre-shared key manager — CRUD + ensure().

API domain: /api/ipsec/pre_shared_keys
Payload key: preSharedKey
Match key:   description (unique PSK description)
Entity suffix: Item
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IpsecPskManager(BaseManager):
    """Manage OPNsense IPsec pre-shared keys."""

    _endpoint = "ipsec/pre_shared_keys"
    _payload_key = "preSharedKey"
    _entity_suffix = "Item"
    _apply_endpoint = "ipsec/service/reconfigure"
    _match_key = "description"

    REDACT_FIELDS = {"Key"}  # The actual PSK value

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
