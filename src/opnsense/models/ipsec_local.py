# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec local authentication model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/connections``
Payload key: ``local``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecLocal:
    """IPsec local authentication entity from OPNsense ipsec/connections API.

    Attributes:
        description:    Local auth description (required, match key).
        enabled:        Whether the local auth is enabled ('0' or '1').
        connection:     Parent connection UUID.
        auth:           Authentication method.
        id:             Local identity.
        eap_id:         EAP identity.
        round:          Authentication round.
        uuid:           Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    connection: str = ""
    auth: str = ""
    id: str = ""
    eap_id: str = ""
    round: str = "0"
    uuid: str = ""
