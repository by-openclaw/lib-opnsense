# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense trust CA manager — CRUD + ensure() for certificate authorities.

API domain: /api/trust/ca
Payload key: ca
Match key:   descr (unique CA description)
Entity suffix: '' (bare: search, get, add, set, del)

Endpoints:
    search  GET  trust/ca/search
    get     GET  trust/ca/get/{uuid}
    create  POST trust/ca/add
    update  POST trust/ca/set/{uuid}
    delete  POST trust/ca/del/{uuid}
    apply   None — trust changes apply immediately

Redact fields: prv, prv_payload
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class TrustCaManager(BaseManager):
    """Manage OPNsense certificate authorities via /api/trust/ca.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Supports both internal CA generation and importing existing CA certificates.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = TrustCaManager(client)
            result = await mgr.ensure("present", {
                "descr": "Internal Root CA",
                "action": "internal",
                "key_type": "4096",
                "digest": "sha256",
                "lifetime": "3650",
                "commonname": "Internal Root CA",
            })

    Input (ensure present):
        descr:        CA description, max 255 (required)
        action:       Generation action — 'existing' (import) or 'internal' (generate)
        key_type:     Key size (e.g. '2048', '4096')
        digest:       Hash algorithm (e.g. 'sha256', 'sha384')
        lifetime:     Validity in days, min 1
        commonname:   Certificate common name, max 255
        country:      Country code
        state:        State or province
        city:         City or locality
        organization: Organization name
        email:        Contact email
        crt_payload:  PEM certificate for import (action=existing)
        prv_payload:  PEM private key for import (action=existing)
        caref:        Parent CA UUID for intermediate CAs

    REDACT_FIELDS: prv, prv_payload — never exposed in before/after dicts.

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "trust/ca"
    _payload_key = "ca"
    _entity_suffix = ""  # trust/ca uses bare names: search, get, add, set, del
    _apply_endpoint = None  # Trust changes apply immediately
    _match_key = "descr"

    REDACT_FIELDS: set[str] = {"prv", "prv_payload"}

    _validators = {
        "descr": {"type": "str", "required": True, "max_length": 255},
        "action": {"type": "enum", "values": ["existing", "internal"]},
        "key_type": {"type": "str"},
        "digest": {"type": "str"},
        "lifetime": {"type": "int", "min": 1},
        "commonname": {"type": "str", "max_length": 255},
        "country": {"type": "str"},
        "state": {"type": "str"},
        "city": {"type": "str"},
        "organization": {"type": "str"},
        "email": {"type": "str"},
        "crt_payload": {"type": "str"},
        "prv_payload": {"type": "str"},
        "caref": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the trust CA manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
