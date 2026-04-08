# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec pre-shared key model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/pre_shared_keys``
Payload key: ``preSharedKey``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecPsk:
    """IPsec pre-shared key entity from OPNsense ipsec/pre_shared_keys API.

    Attributes:
        description:    PSK description (required, match key).
        ident:          Local identity.
        remote_ident:   Remote identity.
        keyType:        Key type (e.g. 'PSK').
        Key:            Pre-shared key value (redacted in output).
        uuid:           Resource UUID assigned by OPNsense.
    """

    description: str
    ident: str = ""
    remote_ident: str = ""
    keyType: str = "PSK"
    Key: str = ""
    uuid: str = ""
