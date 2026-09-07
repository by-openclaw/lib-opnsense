# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound general settings model — typed frozen dataclass.

Maps to OPNsense API: ``/api/unbound/settings`` (``general`` block)
Payload key: ``unbound`` → ``general``

Captures the scalar and enum fields of the resolver's general config. The
``advanced`` block and the sub-resource collections (forwards, DoT, ACLs,
host overrides, aliases, DNSBL) are managed elsewhere — intentionally NOT
modelled here.

Schema discovered from ``GET /api/unbound/settings/get`` on OPNsense 26.7.3.
Reference: https://docs.opnsense.org/manual/unbound.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UbSettings:
    """Unbound resolver ``general`` settings.

    Attributes:
        enabled:            Master enable flag (``'0'`` | ``'1'``). A fresh
                            firewall ships with ``'0'``.
        port:               Listening port (default ``'53'``).
        active_interface:   CSV of interface slot ids to listen on
                            (empty = all; multi-select on the API).
        outgoing_interface: CSV of interface slot ids used for upstream
                            queries (empty = all).
        stats:              Collect resolver statistics.
        dnssec:             Enable DNSSEC validation.
        dns64:              Enable DNS64 synthesis.
        dns64prefix:        DNS64 prefix (blank = default ``64:ff9b::/96``).
        noarecords:         Do not return A records (IPv6-only networks).
        regdhcp:            Register DHCP leases in DNS.
        regdhcpdomain:      Domain suffix for registered DHCP names.
        regdhcpstatic:      Register static DHCP mappings in DNS.
        noreglladdr6:       Do not register IPv6 link-local addresses.
        noregrecords:       Do not register system A/AAAA records.
        txtsupport:         Register DHCP client descriptions as TXT.
        cacheflush:         Flush the cache on every reload.
        safesearch:         Force SafeSearch on major engines.
        local_zone_type:    Local zone type (``transparent`` default; one of
                            ``always_nxdomain``, ``always_refuse``,
                            ``always_transparent``, ``deny``, ``inform``,
                            ``inform_deny``, ``nodefault``, ``refuse``,
                            ``static``, ``transparent``, ``typetransparent``).
        enable_wpad:        Serve WPAD records.
    """

    enabled: str = "0"
    port: str = "53"
    active_interface: str = ""
    outgoing_interface: str = ""
    stats: str = "0"
    dnssec: str = "0"
    dns64: str = "0"
    dns64prefix: str = ""
    noarecords: str = "0"
    regdhcp: str = "0"
    regdhcpdomain: str = ""
    regdhcpstatic: str = "0"
    noreglladdr6: str = "0"
    noregrecords: str = "0"
    txtsupport: str = "0"
    cacheflush: str = "0"
    safesearch: str = "0"
    local_zone_type: str = "transparent"
    enable_wpad: str = "0"
