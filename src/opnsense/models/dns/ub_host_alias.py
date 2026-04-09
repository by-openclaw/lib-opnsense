# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS host alias model — typed frozen dataclass.

Maps to OPNsense API: ``/api/unbound/settings``
Payload key: ``alias``
Match keys: ``['hostname', 'domain']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UbHostAlias:
    """Unbound DNS host alias entity from OPNsense unbound/settings API.

    Attributes:
        hostname:    Hostname for the alias (required).
        domain:      Domain name.
        host:        Parent HostOverride UUID.
        enabled:     Whether the alias is enabled ('0' or '1').
        description: Human-readable description.
        uuid:        Resource UUID assigned by OPNsense.
    """

    hostname: str
    domain: str = ""
    host: str = ""
    enabled: str = "1"
    description: str = ""
    uuid: str = ""
