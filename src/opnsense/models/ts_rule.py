# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense traffic shaper rule model — typed frozen dataclass.

Maps to OPNsense API: ``/api/trafficshaper/settings``
Payload key: ``rule``
Match keys: ``['description', 'interface', 'proto']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TsRule:
    """Traffic shaper rule entity from OPNsense trafficshaper/settings API.

    Attributes:
        description:  Rule description (required, max 255).
        interface:    Network interface (required).
        proto:        Protocol (ip, ip4, ip6, udp, tcp).
        direction:    Traffic direction ('', in, out).
        enabled:      Whether the rule is enabled ('0' or '1').
        sequence:     Rule priority / sequence number (min 1).
        src_port:     Source port filter.
        dst_port:     Destination port filter.
        uuid:         Resource UUID assigned by OPNsense.
    """

    description: str
    interface: str = ""
    proto: str = "ip"
    direction: str = ""
    enabled: str = "1"
    sequence: str = "1"
    src_port: str = "any"
    dst_port: str = "any"
    uuid: str = ""
