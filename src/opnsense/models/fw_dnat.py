# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall D-NAT (port forward) rule model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/d_nat``
Payload key: ``rule``
Match keys: ``['descr', 'interface', 'target']``

Note: D-NAT uses 'descr' not 'description' (OPNsense API inconsistency).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwDnatRule:
    """D-NAT (port forward) rule entity from OPNsense firewall/d_nat API.

    Attributes:
        descr:        Rule description (required, max 255). Note: 'descr' not 'description'.
        interface:    Interface name (required).
        target:       Destination IP address (required, IPv4/IPv6).
        local_port:   Local port or range (mapped port).
        protocol:     Protocol (e.g. 'TCP', 'UDP').
        ipprotocol:   IP version ('inet', 'inet6', 'inet46').
        disabled:     Whether the rule is disabled ('0' or '1').
        uuid:         Resource UUID assigned by OPNsense.
    """

    descr: str
    interface: str = ""
    target: str = ""
    local_port: str = ""
    protocol: str = ""
    ipprotocol: str = "inet"
    disabled: str = "0"
    uuid: str = ""
