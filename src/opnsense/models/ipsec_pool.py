# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec pool model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/pools``
Payload key: ``pool``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecPool:
    """IPsec address pool entity from OPNsense ipsec/pools API.

    Attributes:
        name:       Pool name (required, match key).
        enabled:    Whether the pool is enabled ('0' or '1').
        addrs:      IP pool range/CIDR.
        dns:        DNS server(s) pushed to peers.
        uuid:       Resource UUID assigned by OPNsense.
    """

    name: str
    enabled: str = "1"
    addrs: str = ""
    dns: str = ""
    uuid: str = ""
