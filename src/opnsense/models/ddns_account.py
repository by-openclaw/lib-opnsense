# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense DynDNS account model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dyndns/accounts``
Payload key: ``account``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DdnsAccount:
    """DynDNS account entity from OPNsense dyndns/accounts API.

    Attributes:
        description:      Account description (required, max 255).
        enabled:          Whether the account is enabled ('0' or '1').
        service:          DynDNS service provider (e.g. 'cloudflare', 'aws', 'custom').
        protocol:         Protocol identifier.
        server:           Server hostname.
        username:         Authentication username.
        password:         Authentication password.
        resourceId:       Resource identifier (e.g. zone ID).
        zone:             DNS zone.
        wildcard:         Enable wildcard ('0' or '1').
        checkip:          IP check method (e.g. 'web_cloudflare').
        checkip_timeout:  IP check timeout in seconds.
        force_ssl:        Force SSL ('0' or '1').
        ttl:              TTL in seconds.
        interface:        Network interface.
        uuid:             Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    service: str = "cloudflare"
    protocol: str = ""
    server: str = ""
    username: str = ""
    password: str = ""
    resourceId: str = ""
    hostnames: str = ""
    zone: str = ""
    wildcard: str = "0"
    checkip: str = "web_cloudflare"
    checkip_timeout: str = "10"
    force_ssl: str = "1"
    ttl: str = "300"
    interface: str = ""
    uuid: str = ""
