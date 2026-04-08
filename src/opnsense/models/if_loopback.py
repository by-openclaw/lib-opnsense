# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface loopback model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/loopback_settings``
Payload key: ``loopback``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfLoopback:
    """Loopback interface entity from OPNsense interfaces/loopback_settings API.

    Attributes:
        description: Description (match key, required). Note: 'description' not 'descr'.
        deviceId:    Device identifier (read-only, assigned by OPNsense).
        uuid:        Resource UUID assigned by OPNsense.
    """

    description: str
    deviceId: str = ""
    uuid: str = ""
