# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP boot/PXE entry model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``boot``
Match keys:  ``interface`` + ``filename``

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqBoot:
    """DHCP boot/PXE configuration entry.

    Attributes:
        interface:   Interface slot (optional — empty = all).
        tag:         Optional DHCP tag list (comma-separated or list).
        filename:    PXE boot file name (required).
        servername:  TFTP server name (optional).
        address:     TFTP server address (optional).
        description: Free-text description.
        uuid:        Resource UUID.
    """

    interface: str = ""
    tag: str = ""
    filename: str = ""
    servername: str = ""
    address: str = ""
    description: str = ""
    uuid: str = ""
