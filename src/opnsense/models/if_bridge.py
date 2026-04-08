# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface bridge model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/bridge_settings``
Payload key: ``bridge``
Match key: ``descr``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfBridge:
    """Bridge interface entity from OPNsense interfaces/bridge_settings API.

    Attributes:
        descr:      Description (match key, required).
        members:    Bridge member interfaces (comma-separated).
        linklocal:  Link-local address ('0' or '1').
        enablestp:  Enable STP ('0' or '1').
        proto:      STP protocol ('rstp', 'stp').
        uuid:       Resource UUID assigned by OPNsense.
    """

    descr: str
    members: str = ""
    linklocal: str = "0"
    enablestp: str = "0"
    proto: str = "rstp"
    uuid: str = ""
