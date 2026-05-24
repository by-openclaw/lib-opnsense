# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP range model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``range``
Match keys:  ``interface`` + ``start_addr`` (composite)

A range defines a DHCP4 or DHCP6 lease pool for a given interface:
  * **IPv4**: ``interface`` + ``subnet_mask`` (dotted, e.g. ``255.255.255.0``)
    + ``start_addr`` + ``end_addr``. Do NOT set ``constructor`` / ``prefix_len``.
  * **IPv6**: ``constructor`` (interface providing the prefix) + ``prefix_len``
    + ``start_addr`` / ``end_addr`` as partial addresses (e.g. ``::1000``).
    May also set ``ra_mode`` / ``ra_priority`` etc. for Router Advertisements
    on the same range.

Schema discovered from ``GET /api/dnsmasq/settings/getRange`` on OPNsense 26.1.
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqRange:
    """Per-interface DHCP4 or DHCP6 pool entry.

    Attributes (selected — see manager docstring for full list):
        interface:           OPNsense interface slot (e.g. ``'lan'``).
        set_tag:             DHCP tag UUID (optional).
        start_addr:          Pool start IP (v4) or partial address (v6).
        end_addr:            Pool end IP (v4) or partial address (v6).
        subnet_mask:         IPv4 only — dotted mask, e.g. ``'255.255.255.0'``.
        constructor:         IPv6 only — interface providing the GUA/ULA prefix.
        mode:                IPv6 only — DHCPv6 mode toggle list (multi-select).
        prefix_len:          IPv6 only — prefix length when constructor set.
        lease_time:          Lease lifetime in **integer seconds** as a
                             string (e.g. ``'3600'`` = 1h). The API rejects
                             human-readable suffixes like ``'1h'``.
        domain_type:         ``'range'`` (default) | ``'interface'``.
        domain:              Domain to advertise in DHCP option 15.
        nosync:              ``'1'`` to disable lease syncing.
        ra_mode:             RA mode (IPv6) — slaac / ra-stateless / ...
        ra_priority:         RA preference (``'low'``/``'medium'``/``'high'``).
        ra_mtu:              MTU advertised in RA.
        ra_interval:         RA broadcast interval.
        ra_router_lifetime:  RA router lifetime.
        description:         Free-text label.
        uuid:                Resource UUID assigned by OPNsense.
    """

    interface: str = ""
    set_tag: str = ""
    start_addr: str = ""
    end_addr: str = ""
    subnet_mask: str = ""
    constructor: str = ""
    mode: str = ""
    prefix_len: str = ""
    lease_time: str = ""
    domain_type: str = "range"
    domain: str = ""
    nosync: str = "0"
    ra_mode: str = ""
    ra_priority: str = ""
    ra_mtu: str = ""
    ra_interval: str = ""
    ra_router_lifetime: str = ""
    description: str = ""
    uuid: str = ""
