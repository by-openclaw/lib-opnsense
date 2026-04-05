# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS ACL manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: acl
Match key:   name (unique ACL name)
Entity suffix: Acl (search_acl, get_acl, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbAclManager(BaseManager):
    """Manage Unbound DNS access control lists."""

    _endpoint = "unbound/settings"
    _payload_key = "acl"
    _entity_suffix = "Acl"
    _apply_endpoint = "unbound/service/reconfigure"
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
