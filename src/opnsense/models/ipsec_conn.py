# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec connection model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/connections``
Payload key: ``connection``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecConn:
    """IPsec connection entity from OPNsense ipsec/connections API.

    Attributes:
        description:    Connection description (required, match key).
        enabled:        Whether the connection is enabled ('0' or '1').
        version:        IKE version.
        aggressive:     Aggressive mode ('0' or '1').
        mobike:         MOBIKE support ('0' or '1').
        reauth_time:    Re-authentication time in seconds.
        rekey_time:     Re-keying time in seconds.
        dpd_delay:      DPD delay in seconds.
        dpd_timeout:    DPD timeout in seconds.
        keyingtries:    Number of keying tries.
        uuid:           Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    version: str = ""
    aggressive: str = "0"
    mobike: str = "1"
    reauth_time: str = ""
    rekey_time: str = ""
    dpd_delay: str = ""
    dpd_timeout: str = ""
    keyingtries: str = ""
    uuid: str = ""
