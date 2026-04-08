# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface VXLAN model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/vxlan_settings``
Payload key: ``vxlan``
Match keys: ``['vxlanid', 'vxlanlocal']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfVxlan:
    """VXLAN interface entity from OPNsense interfaces/vxlan_settings API.

    Attributes:
        vxlanid:          VXLAN Network Identifier (1-16777215, required).
        vxlanlocal:       Local VTEP address (required).
        vxlanlocalport:   Local UDP port.
        vxlanremote:      Remote VTEP address.
        vxlanremoteport:  Remote UDP port.
        uuid:             Resource UUID assigned by OPNsense.
    """

    vxlanid: str
    vxlanlocal: str = ""
    vxlanlocalport: str = ""
    vxlanremote: str = ""
    vxlanremoteport: str = ""
    uuid: str = ""
