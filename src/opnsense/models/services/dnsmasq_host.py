# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq host entry model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``host``
Match keys:  ``host`` + ``domain`` (composite, forms the FQDN identity)

A Dnsmasq host entry can serve two roles, often combined:
  * DNS A/AAAA record (``host`` + ``domain`` + ``ip``)
  * DHCP reservation (``hwaddr`` + ``ip``, optionally with ``host``/``domain``
    for DNS registration of the lease)

Schema discovered from ``GET /api/dnsmasq/settings/getHost`` on OPNsense 26.1.
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqHost:
    """Per-host Dnsmasq DNS/DHCP entry.

    Attributes:
        host:        Short hostname (e.g. ``'printer-01'``). With ``domain``
                     forms the FQDN that uniquely identifies the entry.
        domain:      Domain (e.g. ``'lan.example.com'``). Pure DHCP-only
                     reservations may leave both ``host`` and ``domain``
                     empty — in that case ``hwaddr`` distinguishes entries.
        local:       Local-only ``'0'``/``'1'`` — when ``'1'`` the entry is
                     not propagated upstream.
        ip:          IP address (single string on write; comes back as an
                     enum dict on ``getHost``).
        cnames:      CNAME aliases (CSV).
        client_id:   DHCP client identifier.
        hwaddr:      MAC address for DHCP reservations.
        lease_time:  Override DHCP lease time (e.g. ``'12h'``).
        ignore:      ``'1'`` to suppress this entry without deleting it.
        set_tag:     DHCP tag association (references a `dhcp_tag` UUID).
        descr:       Free-text description.
        comments:    Multi-line comments.
        aliases:     Additional alias names.
        uuid:        Resource UUID assigned by OPNsense.
    """

    host: str = ""
    domain: str = ""
    local: str = "0"
    ip: str = ""
    cnames: str = ""
    client_id: str = ""
    hwaddr: str = ""
    lease_time: str = ""
    ignore: str = "0"
    set_tag: str = ""
    descr: str = ""
    comments: str = ""
    aliases: str = ""
    uuid: str = ""
