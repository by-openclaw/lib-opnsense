# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS forwarding domain model — typed frozen dataclass.

Maps to OPNsense API: ``/api/unbound/settings``
Payload key: ``forward``
Match keys: ``['domain', 'server']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UbForward:
    """Unbound DNS forwarding domain entity from OPNsense unbound/settings API.

    Attributes:
        domain:               Domain to forward queries for (required).
        server:               Upstream DNS server address.
        type:                 Forward type ('forward' or 'stub').
        port:                 Upstream DNS server port.
        verify:               TLS verification hostname.
        forward_tcp_upstream: Use TCP for upstream queries ('0' or '1').
        forward_first:        Try forwarding first, then resolve ('0' or '1').
        enabled:              Whether the forward is enabled ('0' or '1').
        description:          Human-readable description.
        uuid:                 Resource UUID assigned by OPNsense.
    """

    domain: str
    server: str = ""
    type: str = "forward"
    port: str = ""
    verify: str = ""
    forward_tcp_upstream: str = "0"
    forward_first: str = "0"
    enabled: str = "1"
    description: str = ""
    uuid: str = ""
