# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 subnet model — typed frozen dataclass.

Maps to OPNsense API: ``/api/kea/dhcpv4``
Payload key: ``subnet4``
Match key: ``subnet``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kea4Subnet:
    """Kea DHCPv4 subnet entity from OPNsense kea/dhcpv4 API.

    Attributes:
        subnet:                 Subnet CIDR (required, max 255).
        pools:                  Address pool range(s).
        next_server:            TFTP/PXE next-server address.
        option_data_autocollect: Auto-collect option data ('0' or '1').
        description:            Human-readable description (max 255).
        uuid:                   Resource UUID assigned by OPNsense.
    """

    subnet: str
    pools: str = ""
    next_server: str = ""
    option_data_autocollect: str = "1"
    description: str = ""
    uuid: str = ""
