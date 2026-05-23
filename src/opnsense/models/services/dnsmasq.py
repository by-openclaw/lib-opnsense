# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq global settings model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``dnsmasq``

Captures the scalar and enum fields of the Dnsmasq global config. The
sub-resource collections (``hosts``, ``domainoverrides``, ``dhcp_ranges``,
``dhcp_options``, ``dhcp_tags``, ``dhcp_boot``) are managed by their own
``Dnsmasq*Manager`` classes — they are intentionally NOT modelled here.

Schema discovered from ``GET /api/dnsmasq/settings/get`` on OPNsense 26.1.
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqSettings:
    """Global Dnsmasq DNS/DHCP/RA daemon settings.

    Attributes:
        enable:           Master enable flag (``'0'`` | ``'1'``).
        regdhcp:          Register DHCP leases as DNS A records.
        regdhcpstatic:    Also register static DHCP mappings.
        dhcpfirst:        Resolve DHCP-registered hosts before upstream DNS.
        strict_order:     Query upstream DNS servers in strict order.
        domain_needed:    Drop reverse lookups without a domain.
        no_private_reverse: Drop reverse lookups for RFC1918 ranges.
        no_resolv:        Ignore /etc/resolv.conf for upstream servers.
        log_queries:      Log every DNS query (high volume).
        no_hosts:         Ignore /etc/hosts when answering queries.
        strictbind:       Bind only to listed interfaces (avoids port grabs
                          on unrelated interfaces — see epic #65 context).
        dnssec:           Enable DNSSEC validation.
        regdhcpdomain:    Domain suffix appended when registering DHCP names.
        interface:        Comma-separated interface slots to listen on
                          (multi-select on the API; the manager normalises
                          list inputs to a comma-separated string).
        port:             Daemon listening port (default ``'53'``; commonly
                          ``'53053'`` when Unbound owns port 53).
        dns_port:         DNS-specific port if separated from ``port``.
        dns_forward_max:  Maximum concurrent forwarded queries (blank = default).
        cache_size:       In-memory cache entry count (blank = default).
        local_ttl:        Override TTL for locally-served records.
        add_mac:          Append client MAC to upstream queries —
                          ``''`` | ``'standard'`` | ``'base64'`` | ``'text'``.
        add_subnet:       Append client subnet (EDNS Client Subnet).
        strip_subnet:     Strip incoming EDNS Client Subnet from forwarded.
        dhcp:             Comma-separated DHCP toggle flags from
                          ``{no_interface, fqdn, domain, local, lease_max,
                          authoritative, ...}``.
        no_ident:         Hide daemon identity string.
    """

    enable: str = "0"
    regdhcp: str = "0"
    regdhcpstatic: str = "0"
    dhcpfirst: str = "0"
    strict_order: str = "0"
    domain_needed: str = "0"
    no_private_reverse: str = "0"
    no_resolv: str = "0"
    log_queries: str = "0"
    no_hosts: str = "0"
    strictbind: str = "0"
    dnssec: str = "0"
    regdhcpdomain: str = ""
    interface: str = ""
    port: str = "53"
    dns_port: str = "53"
    dns_forward_max: str = ""
    cache_size: str = ""
    local_ttl: str = ""
    add_mac: str = ""
    add_subnet: str = "0"
    strip_subnet: str = "0"
    dhcp: str = ""
    no_ident: str = "0"
