# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall NPTv6 rule model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/npt``
Payload key: ``rule``
Match keys: ``['source_net', 'destination_net']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwNptRule:
    """NPTv6 (NAT66) rule entity from OPNsense firewall/npt API.

    Attributes:
        source_net:       Source IPv6 prefix (required, max 255).
        destination_net:  Destination IPv6 prefix (max 255).
        interface:        Interface name.
        enabled:          Whether the rule is enabled ('0' or '1').
        log:              Whether to log matches ('0' or '1').
        sequence:         Rule sequence/priority.
        description:      Rule description (max 255).
        trackif:          Track interface.
        categories:       Comma-separated category UUIDs.
        uuid:             Resource UUID assigned by OPNsense.
    """

    source_net: str
    destination_net: str = ""
    interface: str = ""
    enabled: str = "1"
    log: str = "0"
    sequence: str = "100"
    description: str = ""
    trackif: str = ""
    categories: str = ""
    uuid: str = ""
