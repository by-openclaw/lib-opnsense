# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IDS/Suricata policy manager — CRUD + ensure().

API domain: /api/ids/settings
Payload key: policy
Match key:   description (unique policy description)
Entity suffix: Policy (search_policy, get_policy, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class IdsPolicyManager(BaseManager):
    """Manage OPNsense IDS/Suricata policies."""

    _endpoint = "ids/settings"
    _payload_key = "policy"
    _entity_suffix = "Policy"
    _apply_endpoint = "ids/service/reconfigure"
    _match_key = "description"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
