# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 HA peer model — typed frozen dataclass.

Maps to OPNsense API: ``/api/kea/dhcpv4``
Payload key: ``peer``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kea4Peer:
    """Kea DHCPv4 HA peer entity from OPNsense kea/dhcpv4 API.

    Attributes:
        name: Peer name (required, max 255).
        role: HA role ('primary' or 'standby').
        url:  Peer URL for replication.
        uuid: Resource UUID assigned by OPNsense.
    """

    name: str
    role: str = "primary"
    url: str = ""
    uuid: str = ""
