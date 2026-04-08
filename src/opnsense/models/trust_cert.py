# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense trust cert model — typed frozen dataclass.

Maps to OPNsense API: ``/api/trust/cert``
Payload key: ``cert``
Match key: ``descr``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustCert:
    """Certificate entity from OPNsense trust/cert API.

    Attributes:
        descr:          Certificate description (required).
        caref:          Parent CA UUID.
        action:         Generation action — 'internal', 'external', 'existing'.
        key_type:       Key size (e.g. '2048', '4096').
        digest:         Hash algorithm (e.g. 'sha256', 'sha384').
        cert_type:      Certificate type — 'usr_cert' or 'server_cert'.
        lifetime:       Validity in days.
        commonname:     Certificate common name.
        altnames_dns:   SAN DNS names, comma-separated.
        altnames_ip:    SAN IP addresses, comma-separated.
        altnames_email: SAN email addresses.
        altnames_uri:   SAN URIs.
        country:        Country code.
        state:          State or province.
        city:           City or locality.
        organization:   Organization name.
        email:          Contact email.
        crt_payload:    PEM certificate for import.
        prv_payload:    PEM private key for import (redacted in output).
        csr_payload:    CSR for signing (redacted in output).
        uuid:           Resource UUID assigned by OPNsense.
    """

    descr: str
    caref: str = ""
    action: str = "internal"
    key_type: str = "2048"
    digest: str = "sha256"
    cert_type: str = "server_cert"
    lifetime: str = "397"
    commonname: str = ""
    altnames_dns: str = ""
    altnames_ip: str = ""
    altnames_email: str = ""
    altnames_uri: str = ""
    country: str = ""
    state: str = ""
    city: str = ""
    organization: str = ""
    email: str = ""
    crt_payload: str = ""
    prv_payload: str = ""
    csr_payload: str = ""
    uuid: str = ""
