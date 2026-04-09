# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec child SA model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/connections``
Payload key: ``child``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecChild:
    """IPsec child SA entity from OPNsense ipsec/connections API.

    Attributes:
        description:    Child SA description (required, match key).
        enabled:        Whether the child SA is enabled ('0' or '1').
        connection:     Parent connection UUID.
        mode:           IPsec mode (e.g. 'tunnel', 'transport').
        policies:       Install policies ('0' or '1').
        rekey_time:     Re-keying time in seconds.
        sha256_96:      SHA-256-96 compatibility ('0' or '1').
        uuid:           Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    connection: str = ""
    mode: str = "tunnel"
    policies: str = "1"
    rekey_time: str = "3600"
    sha256_96: str = "0"
    uuid: str = ""
