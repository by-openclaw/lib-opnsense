# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall filter rule model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/filter``
Payload key: ``rule``
Match keys: ``['description', 'interface', 'direction', 'protocol']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwFilterRule:
    """Firewall filter rule entity from OPNsense firewall/filter API.

    Attributes:
        description:      Rule description (required, max 255).
        action:           Rule action ('pass', 'block', 'reject').
        interface:        Interface name (required).
        direction:        Traffic direction ('in', 'out', 'any').
        protocol:         Protocol (e.g. 'TCP', 'UDP', 'ICMP').
        ipprotocol:       IP version ('inet', 'inet6', 'inet46').
        source_net:       Source network/address (max 255).
        destination_net:  Destination network/address (max 255).
        source_port:      Source port or range (max 255).
        destination_port: Destination port or range (max 255).
        enabled:          Whether the rule is enabled ('0' or '1').
        log:              Whether to log matches ('0' or '1').
        quick:            Whether to apply quick match ('0' or '1').
        source_not:       Invert source match ('0' or '1').
        destination_not:  Invert destination match ('0' or '1').
        interfacenot:     Invert interface match ('0' or '1').
        gateway:          Policy routing gateway.
        categories:       Comma-separated category UUIDs.
        icmptype:         ICMP types, comma-separated.
        icmp6type:        ICMPv6 types, comma-separated.
        statetype:        State type ('keep', 'sloppy', 'modulate', 'synproxy').
        tag:              PF tag to apply.
        tagged:           Match PF tag.
        nosync:           No XML sync ('0' or '1').
        uuid:             Resource UUID assigned by OPNsense.
    """

    description: str
    action: str = "pass"
    interface: str = ""
    direction: str = "in"
    protocol: str = ""
    ipprotocol: str = "inet"
    source_net: str = ""
    destination_net: str = ""
    source_port: str = ""
    destination_port: str = ""
    enabled: str = "1"
    log: str = "0"
    quick: str = "1"
    sequence: str = ""
    source_not: str = "0"
    destination_not: str = "0"
    interfacenot: str = "0"
    gateway: str = ""
    categories: str = ""
    icmptype: str = ""
    icmp6type: str = ""
    statetype: str = ""
    tag: str = ""
    tagged: str = ""
    nosync: str = "0"
    uuid: str = ""
