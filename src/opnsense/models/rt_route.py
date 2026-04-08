# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense routing route model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/routes/routes``
Payload key: ``route``
Match keys: ``['network', 'gateway']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RtRoute:
    """Routing route entity from OPNsense routes/routes API.

    Attributes:
        network:   Destination network (required, composite match key).
        gateway:   Gateway UUID or name (required, composite match key).
        descr:     Description (max 255).
        disabled:  Disabled flag ('0' or '1').
        uuid:      Resource UUID assigned by OPNsense.
    """

    network: str
    gateway: str = ""
    descr: str = ""
    disabled: str = "0"
    uuid: str = ""
