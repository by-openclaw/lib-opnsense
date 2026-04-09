# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv6 subnet model — typed frozen dataclass.

Maps to OPNsense API: ``/api/kea/dhcpv6``
Payload key: ``subnet6``
Match key: ``subnet``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kea6Subnet:
    """Kea DHCPv6 subnet entity from OPNsense kea/dhcpv6 API.

    Attributes:
        subnet:      Subnet CIDR (required, max 255).
        description: Human-readable description (max 255).
        uuid:        Resource UUID assigned by OPNsense.
    """

    subnet: str
    description: str = ""
    uuid: str = ""
