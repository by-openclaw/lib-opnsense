# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense routing gateway model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/routing/settings``
Payload key: ``gateway_item``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RtGateway:
    """Routing gateway entity from OPNsense routing/settings API.

    Attributes:
        name:        Gateway name (required, match key).
        interface:   Interface name (required).
        gateway:     Gateway IP address (required).
        ipprotocol:  IP protocol ('inet' or 'inet6').
        defaultgw:   Default gateway flag ('0' or '1').
        disabled:    Disabled flag ('0' or '1').
        descr:       Description.
        priority:    Priority (0-255).
        weight:      Weight (1-5).
        uuid:        Resource UUID assigned by OPNsense.
    """

    name: str
    interface: str = ""
    gateway: str = ""
    ipprotocol: str = "inet"
    defaultgw: str = "0"
    disabled: str = "0"
    descr: str = ""
    priority: str = "255"
    weight: str = "1"
    uuid: str = ""
