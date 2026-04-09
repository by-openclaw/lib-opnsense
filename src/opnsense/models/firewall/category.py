# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall category model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/category``
Payload key: ``category``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwCategory:
    """Firewall category entity from OPNsense firewall/category API.

    Attributes:
        name:   Category name (required, max 255).
        color:  Hex color (6 digits, no # prefix, e.g. 'ff0000').
        uuid:   Resource UUID assigned by OPNsense.
    """

    name: str
    color: str = ""
    uuid: str = ""
