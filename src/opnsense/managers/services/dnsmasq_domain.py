# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq domain override manager — per-domain DNS forwarder CRUD.

API domain: /api/dnsmasq/settings
Payload key: domainoverride (NOT 'domain' or 'domains' — verified via probe)
Match keys:  domain + ip (composite — multiple upstream servers per domain are
             legitimate for HA, so the destination IP is part of identity)
Entity suffix: Domain (searchDomain, getDomain, addDomain, setDomain, delDomain, toggleDomain)

Endpoints:
    search  POST dnsmasq/settings/searchDomain
    get     GET  dnsmasq/settings/getDomain/{uuid}
    create  POST dnsmasq/settings/addDomain
    update  POST dnsmasq/settings/setDomain/{uuid}
    delete  POST dnsmasq/settings/delDomain/{uuid}
    toggle  POST dnsmasq/settings/toggleDomain/{uuid}/{enabled}
    apply   POST dnsmasq/service/reconfigure

Redact fields: none
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DnsmasqDomainManager(BaseManager):
    """Manage OPNsense Dnsmasq domain overrides via /api/dnsmasq/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. Identity is the
    ``domain``+``ip`` composite — same domain forwarded to a different upstream
    server is a distinct entry.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnsmasqDomainManager(client)
            await mgr.ensure("present", {
                "domain": "internal.example.com",
                "ip": "10.0.0.53",
                "descr": "internal AD DNS",
            })

    Input (ensure present):
        sequence: Evaluation order (optional, default ``'1'``).
        domain:   Forward domain (required).
        ipset:    Optional ipset name.
        srcip:    Optional source IP for forwarded queries.
        port:     Optional upstream port (defaults to 53).
        ip:       Upstream DNS server (required, part of identity).
        descr:    Free-text description.

    Output (EnsureResult):
        changed:  bool — True if state was modified.
        action:   'created' | 'updated' | 'deleted' | 'noop'.
        uuid:     Resource UUID (None on noop absent).
        before:   Previous state dict.
        after:    New state dict.
    """

    _endpoint = "dnsmasq/settings"
    # Body wrapper is 'domainoverride' even though URL suffix is 'Domain' —
    # verified on OPNsense 26.1 via probe.
    _payload_key = "domainoverride"
    _entity_suffix = "Domain"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["domain", "ip"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "sequence": {"type": "str", "max_length": 16},
        "domain": {"type": "str", "required": True, "max_length": 255},
        "ipset": {"type": "str", "max_length": 64},
        "srcip": {"type": "str", "max_length": 128},
        "port": {"type": "str", "max_length": 5},
        "ip": {"type": "str", "required": True, "max_length": 128},
        "descr": {"type": "str", "max_length": 1024},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq domain override manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
