# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense auth group model — typed frozen dataclass.

Maps to OPNsense API: ``/api/auth/group``
Payload key: ``group``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthGroup:
    """Local group entity from OPNsense auth/group API.

    Attributes:
        name:        Group name (unique, alphanumeric + hyphens/underscores, max 32).
        description: Group description (max 255).
        uuid:        Resource UUID assigned by OPNsense.
    """

    name: str
    description: str = ""
    uuid: str = ""
