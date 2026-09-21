# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME validation manager — CRUD + ensure().

API domain: /api/acmeclient/validations  (os-acme-client plugin)
Payload key: validation
Match key:   name
Entity suffix: '' (bare: search, get, add, set, del, toggle)

A validation defines the ACME challenge method: HTTP-01, DNS-01 or TLS-ALPN-01.
The platform uses **DNS-01 via Cloudflare** (``dns_service='dns_cf'``) with a
scoped API token (``dns_cf_token``). The ~120 acme.sh DNS providers each carry
their own ``dns_<provider>_*`` fields; only the common + Cloudflare fields are
validated here — any other provider field passes through ``ensure(params=...)``.

Endpoints:
    search  GET  acmeclient/validations/search
    get     GET  acmeclient/validations/get/{uuid}
    create  POST acmeclient/validations/add
    update  POST acmeclient/validations/update/{uuid}
    delete  POST acmeclient/validations/del/{uuid}
    apply   None — stored immediately; reconfigure via AcmeServiceManager.

Redact fields: Cloudflare + common DNS provider secrets (see REDACT_FIELDS).
Reference: https://github.com/opnsense/plugins/tree/master/security/acme-client
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class AcmeValidationManager(BaseManager):
    """Manage os-acme-client challenge validations via /api/acmeclient/validations.

    Inherits the full CRUD + ``ensure()`` lifecycle from :class:`BaseManager`.

    Usage (Cloudflare DNS-01)::

        async with OpnsenseClient(...) as client:
            mgr = AcmeValidationManager(client)
            await mgr.ensure("present", {
                "name": "cloudflare-dns",
                "method": "dns01",
                "dns_service": "dns_cf",
                "dns_cf_token": "<scoped-token>",
                "dns_cf_account_id": "<account-id>",
            })

    Input (ensure present) — common fields:
        name:        Validation name (required, match key).
        method:      'http01' / 'dns01' / 'tlsalpn01'.
        description: Free-text description.
        enabled:     '1' / '0'.
        http_service: HTTP-01 server — 'opnsense' / 'haproxy'.
        dns_service: acme.sh DNS provider id ('dns_cf' = Cloudflare).
        dns_sleep:   Seconds to wait for DNS propagation.
        dns_cf_token / dns_cf_key / dns_cf_email / dns_cf_account_id /
        dns_cf_zone_id: Cloudflare credentials (token model preferred).
        (Any other ``dns_<provider>_*`` field passes through untouched.)

    REDACT_FIELDS: Cloudflare + common provider secrets.

    Output (EnsureResult): standard created/updated/deleted/noop.
    """

    _endpoint = "acmeclient/validations"
    _payload_key = "validation"
    _entity_suffix = ""
    _update_action = "update"  # acmeclient: set/{uuid} says "saved" but is the whole-model setter
    _apply_endpoint = None
    _match_key = "name"

    # Secret-bearing fields across the common DNS providers. Redaction is by
    # exact field name; add a provider's secret field here if you adopt it.
    REDACT_FIELDS: set[str] = {
        # Cloudflare (platform provider)
        "dns_cf_token",
        "dns_cf_key",
        # Common providers
        "dns_aws_secret",
        "dns_ali_secret",
        "dns_azuredns_clientsecret",
        "dns_gd_secret",
        "dns_cx_secret",
        "dns_do_password",
        "dns_dyn_password",
        "dns_dynu_secret",
        "dns_gandi_livedns_key",
        "dns_gcloud_key",
        "dns_dp_key",
        "dns_dh_key",
        "dns_ad_key",
        "dns_da_key",
    }

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "description": {"type": "str", "max_length": 255},
        "method": {"type": "enum", "values": ["http01", "dns01", "tlsalpn01"]},
        "enabled": {"type": "bool_str"},
        "http_service": {"type": "enum", "values": ["opnsense", "haproxy"]},
        "http_opn_autodiscovery": {"type": "bool_str"},
        "dns_service": {"type": "str", "max_length": 64},
        "dns_sleep": {"type": "str", "max_length": 10},
        "dns_cf_email": {"type": "str", "max_length": 255},
        "dns_cf_key": {"type": "str", "max_length": 255},
        "dns_cf_token": {"type": "str", "max_length": 255},
        "dns_cf_account_id": {"type": "str", "max_length": 255},
        "dns_cf_zone_id": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the ACME validation manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
