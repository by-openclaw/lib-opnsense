# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense trust CA model — typed frozen dataclass.

Maps to OPNsense API: ``/api/trust/ca``
Payload key: ``ca``
Match key: ``descr``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustCa:
    """Certificate authority entity from OPNsense trust/ca API.

    Attributes:
        descr:        CA description (required).
        action:       Generation action — 'existing' or 'internal'.
        key_type:     Key size (e.g. '2048', '4096').
        digest:       Hash algorithm (e.g. 'sha256', 'sha384').
        lifetime:     Validity in days.
        commonname:   Certificate common name.
        country:      Country code.
        state:        State or province.
        city:         City or locality.
        organization: Organization name.
        email:        Contact email.
        crt_payload:  PEM certificate for import.
        prv_payload:  PEM private key for import (redacted in output).
        caref:        Parent CA UUID for intermediate CAs.
        uuid:         Resource UUID assigned by OPNsense.
    """

    descr: str
    action: str = "internal"
    key_type: str = "2048"
    digest: str = "sha256"
    lifetime: str = "825"
    commonname: str = ""
    country: str = ""
    state: str = ""
    city: str = ""
    organization: str = ""
    email: str = ""
    crt_payload: str = ""
    prv_payload: str = ""
    caref: str = ""
    uuid: str = ""
