# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface virtual IP model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/vip_settings``
Payload key: ``vip``
Match keys: ``['address', 'interface', 'mode']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfVip:
    """Virtual IP entity from OPNsense interfaces/vip_settings API.

    Attributes:
        address:    IP address (required).
        interface:  Interface name (required).
        mode:       VIP mode ('ipalias', 'carp', 'proxyarp', 'other', required).
        network:    Network prefix length.
        descr:      Description (max 255). Note: 'descr' not 'description'.
        password:   CARP password (redacted in results).
        uuid:       Resource UUID assigned by OPNsense.
    """

    address: str
    interface: str = ""
    mode: str = "ipalias"
    network: str = ""
    descr: str = ""
    password: str = ""
    uuid: str = ""
