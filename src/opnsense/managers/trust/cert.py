# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense trust cert manager — CRUD + ensure() for certificates.

API domain: /api/trust/cert
Payload key: cert
Match key:   descr (unique certificate description)
Entity suffix: '' (bare: search, get, add, set, del)

Endpoints:
    search  GET  trust/cert/search
    get     GET  trust/cert/get/{uuid}
    create  POST trust/cert/add
    update  POST trust/cert/set/{uuid}
    delete  POST trust/cert/del/{uuid}
    apply   None — trust changes apply immediately

Redact fields: prv, prv_payload, csr_payload
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class TrustCertManager(BaseManager):
    """Manage OPNsense certificates via /api/trust/cert.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Supports internal generation, external CSR signing, and importing existing certs.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = TrustCertManager(client)
            result = await mgr.ensure("present", {
                "descr": "Web Server Cert",
                "caref": "ca-uuid-here",
                "action": "internal",
                "cert_type": "server_cert",
                "lifetime": "397",
                "commonname": "web.example.com",
            })

    Input (ensure present):
        descr:          Certificate description, max 255 (required)
        caref:          Parent CA UUID (required for internal certs)
        action:         Generation action — 'internal', 'external', 'existing'
        key_type:       Key size (e.g. '2048', '4096')
        digest:         Hash algorithm (e.g. 'sha256', 'sha384')
        cert_type:      Certificate type — 'usr_cert' or 'server_cert'
        lifetime:       Validity in days, min 1
        commonname:     Certificate common name, max 255
        altnames_dns:   SAN DNS names, comma-separated
        altnames_ip:    SAN IP addresses, comma-separated
        altnames_email: SAN email addresses
        altnames_uri:   SAN URIs
        country:        Country code
        state:          State or province
        city:           City or locality
        organization:   Organization name
        email:          Contact email
        crt_payload:    PEM certificate for import (action=existing)
        prv_payload:    PEM private key for import (action=existing)
        csr_payload:    CSR for signing (action=external)

    REDACT_FIELDS: prv, prv_payload, csr_payload — never exposed in before/after dicts.

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "trust/cert"
    _payload_key = "cert"
    _entity_suffix = ""  # trust/cert uses bare names: search, get, add, set, del
    _apply_endpoint = None  # Trust changes apply immediately
    _match_key = "descr"

    REDACT_FIELDS: set[str] = {"prv", "prv_payload", "csr_payload"}

    _validators = {
        "descr": {"type": "str", "required": True, "max_length": 255},
        "caref": {"type": "str"},
        "action": {"type": "enum", "values": ["internal", "external", "existing"]},
        "key_type": {"type": "str"},
        "digest": {"type": "str"},
        "cert_type": {"type": "enum", "values": ["usr_cert", "server_cert"]},
        "lifetime": {"type": "int", "min": 1},
        "commonname": {"type": "str", "max_length": 255},
        "altnames_dns": {"type": "str"},
        "altnames_ip": {"type": "str"},
        "altnames_email": {"type": "str"},
        "altnames_uri": {"type": "str"},
        "country": {"type": "str"},
        "state": {"type": "str"},
        "city": {"type": "str"},
        "organization": {"type": "str"},
        "email": {"type": "str"},
        "crt_payload": {"type": "str"},
        "prv_payload": {"type": "str"},
        "csr_payload": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the trust cert manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
