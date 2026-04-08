# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS-over-TLS model — typed frozen dataclass.

Maps to OPNsense API: ``/api/unbound/settings``
Payload key: ``dot``
Match keys: ``['server', 'port']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UbDot:
    """Unbound DNS-over-TLS server entity from OPNsense unbound/settings API.

    Attributes:
        server:               DoT server address (required).
        port:                 DoT server port.
        type:                 Forward type ('dot').
        verify:               TLS verification hostname.
        domain:               Domain name.
        forward_tcp_upstream: Use TCP for upstream queries ('0' or '1').
        forward_first:        Try forwarding first, then resolve ('0' or '1').
        enabled:              Whether the DoT server is enabled ('0' or '1').
        description:          Human-readable description.
        uuid:                 Resource UUID assigned by OPNsense.
    """

    server: str
    port: str = "853"
    type: str = "dot"
    verify: str = ""
    domain: str = ""
    forward_tcp_upstream: str = "0"
    forward_first: str = "0"
    enabled: str = "1"
    description: str = ""
    uuid: str = ""
