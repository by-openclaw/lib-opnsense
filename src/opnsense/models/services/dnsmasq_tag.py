# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP tag entry model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``tag``
Match key:   ``tag`` (the unique tag name)

A Dnsmasq tag is a named label used to scope ranges / hosts / options
to a subset of clients (e.g. by interface, by MAC vendor, by class).

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqTag:
    """Named DHCP tag definition.

    Attributes:
        tag:  Unique tag name (required, identity).
        uuid: Resource UUID.
    """

    tag: str = ""
    uuid: str = ""
