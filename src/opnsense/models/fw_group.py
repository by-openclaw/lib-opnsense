# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall interface group model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/group``
Payload key: ``group``
Match key: ``ifname``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwGroup:
    """Firewall interface group entity from OPNsense firewall/group API.

    Attributes:
        ifname:   Group name (required, alphanumeric + underscores, max 32).
        members:  Comma-separated list of interface names (required).
        descr:    Description (max 255). Note: 'descr' not 'description'.
        uuid:     Resource UUID assigned by OPNsense.
    """

    ifname: str
    members: str = ""
    descr: str = ""
    uuid: str = ""
