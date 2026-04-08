# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv6 reservation manager — CRUD + ensure() for DHCPv6 reservations.

API domain: /api/kea/dhcpv6
Payload key: reservation
Match keys:  ['ip_address', 'duid'] (composite)
Entity suffix: Reservation (searchReservation, getReservation, addReservation, ...)

Endpoints:
    search  GET  kea/dhcpv6/searchReservation
    get     GET  kea/dhcpv6/getReservation/{uuid}
    create  POST kea/dhcpv6/addReservation
    update  POST kea/dhcpv6/setReservation/{uuid}
    delete  POST kea/dhcpv6/delReservation/{uuid}
    apply   POST kea/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class Kea6ReservationManager(BaseManager):
    """Manage OPNsense Kea DHCPv6 reservations via /api/kea/dhcpv6.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DHCPv6 reservations map DUIDs to fixed IPv6 addresses.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = Kea6ReservationManager(client)
            result = await mgr.ensure("present", {
                "ip_address": "2001:db8::50",
                "duid": "00:03:00:01:00:11:22:33:44:55",
                "hostname": "printer",
            })

    Input (ensure present):
        ip_address:   Reserved IPv6 address (required)
        duid:         DHCP Unique Identifier (required)
        hostname:     Client hostname, max 255 (optional)
        description:  Description, max 255 (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "kea/dhcpv6"
    _payload_key = "reservation"
    _entity_suffix = "Reservation"
    _apply_endpoint = "kea/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["ip_address", "duid"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "ip_address": {"type": "str", "required": True},
        "duid": {"type": "str", "required": True},
        "hostname": {"type": "str", "max_length": 255},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Kea DHCPv6 reservation manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
