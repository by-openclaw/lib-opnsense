# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec VTI model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/vti``
Payload key: ``vti``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecVti:
    """IPsec VTI entity from OPNsense ipsec/vti API.

    Attributes:
        description:    VTI description (required, match key).
        enabled:        Whether the VTI is enabled ('0' or '1').
        reqid:          Request ID for policy matching.
        local:          Local outer IP address.
        remote:         Remote outer IP address.
        tunnel_local:   Local inner tunnel address.
        tunnel_remote:  Remote inner tunnel address.
        uuid:           Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    reqid: str = ""
    local: str = ""
    remote: str = ""
    tunnel_local: str = ""
    tunnel_remote: str = ""
    uuid: str = ""
