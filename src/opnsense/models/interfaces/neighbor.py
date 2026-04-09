# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface neighbor (ARP/NDP) model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/neighbor_settings``
Payload key: ``neighbor``
Match keys: ``['ipaddress', 'etheraddr']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfNeighbor:
    """Neighbor (ARP/NDP) entry from OPNsense interfaces/neighbor_settings API.

    Attributes:
        ipaddress:  IP address (required).
        etheraddr:  MAC / Ethernet address.
        descr:      Description (max 255).
        uuid:       Resource UUID assigned by OPNsense.
    """

    ipaddress: str
    etheraddr: str = ""
    descr: str = ""
    uuid: str = ""
