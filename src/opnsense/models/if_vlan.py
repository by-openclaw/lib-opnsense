# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface VLAN model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/vlan_settings``
Payload key: ``vlan``
Match keys: ``['tag', 'if']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfVlan:
    """VLAN interface entity from OPNsense interfaces/vlan_settings API.

    Attributes:
        tag:    VLAN tag (1-4094, required).
        if_:    Parent interface name (required). Note: mapped from API field 'if'.
        pcp:    Priority Code Point (0-7).
        descr:  Description (max 255). Note: 'descr' not 'description'.
        uuid:   Resource UUID assigned by OPNsense.
    """

    tag: str
    if_: str = ""
    pcp: str = ""
    descr: str = ""
    uuid: str = ""
