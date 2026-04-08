# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall source NAT rule model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/source_nat``
Payload key: ``rule``
Match keys: ``['description', 'interface', 'source_net']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwSourceNatRule:
    """Source NAT rule entity from OPNsense firewall/source_nat API.

    Attributes:
        description:  Rule description (required, max 255).
        interface:    Interface name (required).
        source_net:   Source network (required).
        target:       NAT target address.
        ipprotocol:   IP version ('inet', 'inet6', 'inet46').
        enabled:      Whether the rule is enabled ('0' or '1').
        source_not:   Invert source match ('0' or '1').
        destination_not: Invert destination match ('0' or '1').
        destination_port: Destination port.
        source_port:  Source port.
        protocol:     Protocol name.
        log:          Whether to log matches ('0' or '1').
        nonat:        Disable NAT ('0' or '1').
        staticnatport: Use static source port ('0' or '1').
        target_port:  Target port.
        categories:   Comma-separated category UUIDs.
        uuid:         Resource UUID assigned by OPNsense.
    """

    description: str
    interface: str = ""
    source_net: str = ""
    target: str = ""
    ipprotocol: str = "inet"
    enabled: str = "1"
    sequence: str = ""
    source_not: str = "0"
    destination_not: str = "0"
    destination_port: str = ""
    source_port: str = ""
    protocol: str = ""
    log: str = "0"
    nonat: str = "0"
    staticnatport: str = "0"
    target_port: str = ""
    categories: str = ""
    uuid: str = ""
