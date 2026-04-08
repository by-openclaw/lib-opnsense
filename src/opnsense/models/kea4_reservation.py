# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 reservation model — typed frozen dataclass.

Maps to OPNsense API: ``/api/kea/dhcpv4``
Payload key: ``reservation``
Match keys: ``['ip_address', 'hw_address']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kea4Reservation:
    """Kea DHCPv4 reservation entity from OPNsense kea/dhcpv4 API.

    Attributes:
        ip_address:  Reserved IPv4 address (required).
        hw_address:  Client MAC address (required).
        hostname:    Client hostname (max 255).
        description: Human-readable description (max 255).
        uuid:        Resource UUID assigned by OPNsense.
    """

    ip_address: str
    hw_address: str = ""
    hostname: str = ""
    description: str = ""
    uuid: str = ""
