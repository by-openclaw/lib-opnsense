# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP option entry model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``option``
Match keys:  ``interface`` + ``option`` + ``option6``
             (one of ``option`` or ``option6`` will be empty per entry)

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqOption:
    """DHCP option entry (v4 ``option`` xor v6 ``option6``).

    Attributes:
        type:        ``'set'`` (default) | ``'match'`` — option semantics.
        option:      DHCPv4 option number (e.g. ``'3'`` for routers). Either
                     this or ``option6`` is required.
        option6:     DHCPv6 option number (alternative to ``option``).
        interface:   Optional interface scope.
        tag:         Optional tag list — apply to matching clients only.
        set_tag:     Optional tag to set when this option matches.
        value:       Option value (e.g. ``'10.0.0.1'`` for router).
        force:       ``'1'`` to always send even when not requested.
        description: Free-text description.
        uuid:        Resource UUID.
    """

    type: str = "set"
    option: str = ""
    option6: str = ""
    interface: str = ""
    tag: str = ""
    set_tag: str = ""
    value: str = ""
    force: str = "0"
    description: str = ""
    uuid: str = ""
