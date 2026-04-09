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
        advbase:    CARP advertisement base interval (1-254).
        advskew:    CARP advertisement skew (0-254).
        vhid:       CARP virtual host ID.
        gateway:    Gateway IP address.
        nobind:     Do not bind ('0' or '1').
        noexpand:   Do not expand ('0' or '1').
        nosync:     No XMLRPC sync ('0' or '1').
        peer:       CARP peer IP address.
        peer6:      CARP peer IPv6 address.
        uuid:       Resource UUID assigned by OPNsense.
    """

    address: str
    interface: str = ""
    mode: str = "ipalias"
    network: str = ""
    descr: str = ""
    password: str = ""
    advbase: str = ""
    advskew: str = ""
    vhid: str = ""
    gateway: str = ""
    nobind: str = "0"
    noexpand: str = "0"
    nosync: str = "0"
    peer: str = ""
    peer6: str = ""
    uuid: str = ""
