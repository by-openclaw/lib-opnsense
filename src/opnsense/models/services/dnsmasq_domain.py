# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq domain override model — typed frozen dataclass.

Maps to OPNsense API: ``/api/dnsmasq/settings``
Payload key: ``domainoverride`` (NOT ``domain`` or ``domains`` — verified via probe)
Match keys:  ``domain`` + ``ip`` (composite — multiple upstream servers per
             domain are legitimate for HA)

A domain override tells Dnsmasq to forward DNS queries for a specific
domain to an explicit upstream server instead of the default resolver.

Schema discovered from ``GET /api/dnsmasq/settings/getDomain`` on OPNsense 26.1.
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DnsmasqDomain:
    """Per-domain DNS forwarder entry.

    Attributes:
        sequence: Evaluation order (default ``'1'``).
        domain:   Domain to forward (required, e.g. ``'internal.example.com'``).
        ipset:    Optional ipset name to populate with resolved IPs.
        srcip:    Optional source IP for forwarded queries.
        port:     Optional upstream DNS port (default 53).
        ip:       Upstream DNS server address (the forwarder target).
        descr:    Free-text description.
        uuid:     Resource UUID assigned by OPNsense.
    """

    sequence: str = "1"
    domain: str = ""
    ipset: str = ""
    srcip: str = ""
    port: str = ""
    ip: str = ""
    descr: str = ""
    uuid: str = ""
