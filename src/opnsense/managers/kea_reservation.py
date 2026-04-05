# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 reservation manager — CRUD + ensure().

API domain: /api/kea/dhcpv4
Payload key: reservation
Match key:   hostname (unique reservation hostname)
Entity suffix: Reservation (search_reservation, get_reservation, etc.)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class KeaReservationManager(BaseManager):
    """Manage Kea DHCPv4 static reservations (MAC -> IP)."""

    _endpoint = "kea/dhcpv4"
    _payload_key = "reservation"
    _entity_suffix = "Reservation"
    _apply_endpoint = "kea/service/reconfigure"
    _match_key = "hostname"

    REDACT_FIELDS: set[str] = set()

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the manager."""
        super().__init__(client)
