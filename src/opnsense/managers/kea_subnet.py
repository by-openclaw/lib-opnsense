# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 subnet manager — CRUD + ensure().

API domain: /api/kea/dhcpv4
Payload key: subnet4
Match key:   subnet (unique subnet CIDR)
Entity suffix: Subnet (search_subnet, get_subnet, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class KeaSubnetManager(BaseManager):
    """Manage Kea DHCPv4 subnets."""

    _endpoint = "kea/dhcpv4"
    _payload_key = "subnet4"
    _entity_suffix = "Subnet"
    _apply_endpoint = "kea/service/reconfigure"
    _match_key = "subnet"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
