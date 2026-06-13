# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME account model — typed frozen dataclass.

Maps to OPNsense API: ``/api/acmeclient/accounts`` (os-acme-client plugin)
Payload key: ``account``
Match key: ``name``

An ACME account binds a contact email + key to a CA directory (e.g. Let's
Encrypt). It must be registered with the CA (``register`` verb) before any
certificate that references it can be signed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcmeAccount:
    """ACME account entity from os-acme-client ``accounts`` API.

    Attributes:
        name:             Account name (match key, required).
        description:      Free-text description.
        email:            Contact email registered with the CA.
        ca:               CA directory — ``letsencrypt``, ``letsencrypt_test``,
                          ``buypass``, ``buypass_test``, ``google``,
                          ``google_test``, ``sslcom``, ``zerossl``, ``custom``.
        custom_ca:        Custom ACME directory URL (when ``ca='custom'``).
        eab_kid:          External Account Binding key identifier (redacted).
        eab_hmac:         External Account Binding HMAC key (redacted).
        key:              Account private key (server-managed; redacted).
        enabled:          ``"1"`` / ``"0"``.
        statusCode:       Last registration status code (read-only).
        statusLastUpdate: Last status timestamp (read-only).
        id:               Internal model id (read-only).
        uuid:             Resource UUID assigned by OPNsense.
    """

    name: str
    description: str = ""
    email: str = ""
    ca: str = "letsencrypt"
    custom_ca: str = ""
    eab_kid: str = ""
    eab_hmac: str = ""
    key: str = ""
    enabled: str = "1"
    statusCode: str = ""
    statusLastUpdate: str = ""
    id: str = ""
    uuid: str = ""
