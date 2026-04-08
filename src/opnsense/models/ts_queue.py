# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense traffic shaper queue model — typed frozen dataclass.

Maps to OPNsense API: ``/api/trafficshaper/settings``
Payload key: ``queue``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TsQueue:
    """Traffic shaper queue entity from OPNsense trafficshaper/settings API.

    Attributes:
        description:   Queue description (required, max 255).
        weight:        Queue weight (1-100, default '100').
        enabled:       Whether the queue is enabled ('0' or '1').
        mask:          Mask type (none, src-ip, dst-ip, src-ip6, dst-ip6).
        codel_enable:  Whether CoDel AQM is enabled ('0' or '1').
        uuid:          Resource UUID assigned by OPNsense.
    """

    description: str
    weight: str = "100"
    enabled: str = "1"
    mask: str = "none"
    codel_enable: str = "0"
    uuid: str = ""
