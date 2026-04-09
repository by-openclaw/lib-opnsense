# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense IPsec key pair model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/ipsec/key_pairs``
Payload key: ``keyPair``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpsecKeypair:
    """IPsec key pair entity from OPNsense ipsec/key_pairs API.

    Attributes:
        name:           Key pair name (required, match key).
        keyType:        Key type (e.g. 'RSA', 'ECDSA').
        publicKey:      Public key PEM.
        privateKey:     Private key PEM (redacted in output).
        keySize:        Key size.
        uuid:           Resource UUID assigned by OPNsense.
    """

    name: str
    keyType: str = "RSA"
    publicKey: str = ""
    privateKey: str = ""
    keySize: str = ""
    uuid: str = ""
