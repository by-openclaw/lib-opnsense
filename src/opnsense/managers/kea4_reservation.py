# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 reservation manager — CRUD + ensure() for DHCP reservations.

API domain: /api/kea/dhcpv4
Payload key: reservation
Match keys:  ['ip_address', 'hw_address'] (composite)
Entity suffix: Reservation (searchReservation, getReservation, addReservation, ...)

Endpoints:
    search  GET  kea/dhcpv4/searchReservation
    get     GET  kea/dhcpv4/getReservation/{uuid}
    create  POST kea/dhcpv4/addReservation
    update  POST kea/dhcpv4/setReservation/{uuid}
    delete  POST kea/dhcpv4/delReservation/{uuid}
    apply   POST kea/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class Kea4ReservationManager(BaseManager):
    """Manage OPNsense Kea DHCPv4 reservations via /api/kea/dhcpv4.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DHCPv4 reservations map MAC addresses to fixed IPv4 addresses.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = Kea4ReservationManager(client)
            result = await mgr.ensure("present", {
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "printer",
            })
    """

    _endpoint = "kea/dhcpv4"
    _payload_key = "reservation"
    _entity_suffix = "Reservation"
    _apply_endpoint = "kea/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["ip_address", "hw_address"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "ip_address": {"type": "ip", "required": True},
        "hw_address": {"type": "mac", "required": True},
        "hostname": {"type": "str", "max_length": 255},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Kea DHCPv4 reservation manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
