# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall alias model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/alias``
Payload key: ``alias``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwAlias:
    """Firewall alias entity from OPNsense firewall/alias API.

    Attributes:
        name:         Alias name (unique, alphanumeric + underscores, max 32).
        type:         Alias type (host, network, port, url, urltable, etc.).
        content:      Alias content — IPs, networks, ports, URLs (max 10000).
        description:  Human-readable description (max 255).
        enabled:      Whether the alias is enabled ('0' or '1').
        updatefreq:   URL table update frequency in days (max 10).
        uuid:         Resource UUID assigned by OPNsense.
    """

    name: str
    type: str = "host"
    content: str = ""
    description: str = ""
    enabled: str = "1"
    updatefreq: str = ""
    uuid: str = ""
