# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS host override model — typed frozen dataclass.

Maps to OPNsense API: ``/api/unbound/settings``
Payload key: ``host``
Match keys: ``['hostname', 'domain', 'server']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UbHostOverride:
    """Unbound DNS host override entity from OPNsense unbound/settings API.

    Attributes:
        hostname:    Hostname for the override (required).
        domain:      Domain name.
        server:      IP address the hostname resolves to.
        rr:          DNS record type (A, AAAA, MX).
        mxprio:      MX priority (when rr=MX).
        mx:          MX target hostname (when rr=MX).
        ttl:         Time-to-live in seconds.
        txtdata:     TXT record data.
        addptr:      Add PTR record ('0' or '1').
        enabled:     Whether the override is enabled ('0' or '1').
        description: Human-readable description.
        uuid:        Resource UUID assigned by OPNsense.
    """

    hostname: str
    domain: str = ""
    server: str = ""
    rr: str = "A"
    mxprio: str = ""
    mx: str = ""
    ttl: str = ""
    txtdata: str = ""
    addptr: str = "1"
    enabled: str = "1"
    description: str = ""
    uuid: str = ""
