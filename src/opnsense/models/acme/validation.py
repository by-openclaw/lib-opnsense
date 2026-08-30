# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME validation model — typed frozen dataclass.

Maps to OPNsense API: ``/api/acmeclient/validations`` (os-acme-client plugin)
Payload key: ``validation``
Match key: ``name``

A validation describes HOW the CA proves domain control (the ACME challenge):
``http01`` (HTTP-01 via the OPNsense web server or HAProxy), ``dns01``
(DNS-01 via one of ~120 acme.sh DNS providers) or ``tlsalpn01`` (TLS-ALPN-01).

This model types the **common** fields plus the **Cloudflare DNS-01** provider
fields (the platform's provider). The remaining ~119 DNS providers each carry
their own ``dns_<provider>_*`` credential fields; those are NOT enumerated here
but pass straight through ``AcmeValidationManager.ensure(params=...)`` — the
manager forwards any dict key to the API.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcmeValidation:
    """ACME challenge/validation entity from os-acme-client ``validations`` API.

    Attributes:
        name:                  Validation name (match key, required).
        description:           Free-text description.
        method:                Challenge type — ``http01`` / ``dns01`` /
                               ``tlsalpn01``.
        enabled:               ``"1"`` / ``"0"``.
        http_service:          HTTP-01 server — ``opnsense`` / ``haproxy``.
        http_opn_autodiscovery: Auto-detect interface for HTTP-01 (``"1"``/``"0"``).
        http_opn_interface:    HTTP-01 listen interface (when not autodiscovery).
        http_opn_ipaddresses:  HTTP-01 listen IP(s).
        tlsalpn_service:       TLS-ALPN-01 service (``acme``).
        tlsalpn_acme_autodiscovery: Auto-detect interface for TLS-ALPN-01.
        tlsalpn_acme_interface: TLS-ALPN-01 listen interface.
        tlsalpn_acme_ipaddresses: TLS-ALPN-01 listen IP(s).
        dns_service:           acme.sh DNS provider id (``dns_cf`` = Cloudflare).
        dns_sleep:             Seconds to wait for DNS propagation.
        dns_cf_email:          Cloudflare account email (legacy global-key auth).
        dns_cf_key:            Cloudflare global API key (redacted; legacy auth).
        dns_cf_token:          Cloudflare scoped API token (redacted; preferred).
        dns_cf_account_id:     Cloudflare account id (token auth).
        dns_cf_zone_id:        Cloudflare zone id (token auth, optional).
        id:                    Internal model id (read-only).
        uuid:                  Resource UUID assigned by OPNsense.
    """

    name: str
    description: str = ""
    method: str = "dns01"
    enabled: str = "1"
    # HTTP-01
    http_service: str = "opnsense"
    http_opn_autodiscovery: str = "1"
    http_opn_interface: str = ""
    http_opn_ipaddresses: str = ""
    # TLS-ALPN-01
    tlsalpn_service: str = "acme"
    tlsalpn_acme_autodiscovery: str = "1"
    tlsalpn_acme_interface: str = ""
    tlsalpn_acme_ipaddresses: str = ""
    # DNS-01 (generic)
    dns_service: str = ""
    dns_sleep: str = "0"
    # DNS-01 — Cloudflare (platform provider)
    dns_cf_email: str = ""
    dns_cf_key: str = ""
    dns_cf_token: str = ""
    dns_cf_account_id: str = ""
    dns_cf_zone_id: str = ""
    id: str = ""
    uuid: str = ""
