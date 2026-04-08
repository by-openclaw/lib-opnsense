# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv6 reservation model — typed frozen dataclass.

Maps to OPNsense API: ``/api/kea/dhcpv6``
Payload key: ``reservation``
Match keys: ``['ip_address', 'duid']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kea6Reservation:
    """Kea DHCPv6 reservation entity from OPNsense kea/dhcpv6 API.

    Attributes:
        ip_address:  Reserved IPv6 address (required).
        duid:        Client DUID (required).
        hw_address:  Client MAC address.
        hostname:    Client hostname (max 255).
        description: Human-readable description (max 255).
        uuid:        Resource UUID assigned by OPNsense.
    """

    ip_address: str
    duid: str = ""
    hw_address: str = ""
    hostname: str = ""
    description: str = ""
    uuid: str = ""
