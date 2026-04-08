# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall one-to-one NAT rule model — typed frozen dataclass.

Maps to OPNsense API: ``/api/firewall/one_to_one``
Payload key: ``rule``
Match keys: ``['description', 'interface', 'source_net']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FwOneToOneRule:
    """One-to-one NAT rule entity from OPNsense firewall/one_to_one API.

    Attributes:
        description:  Rule description (required, max 255).
        interface:    Interface name (required).
        source_net:   Internal source network (required).
        external:     External (public) address.
        disabled:     Whether the rule is disabled ('0' or '1').
        uuid:         Resource UUID assigned by OPNsense.
    """

    description: str
    interface: str = ""
    source_net: str = ""
    external: str = ""
    disabled: str = "0"
    uuid: str = ""
