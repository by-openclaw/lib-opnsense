# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq host entry manager — DNS + DHCP host CRUD + ensure().

API domain: /api/dnsmasq/settings
Payload key: host
Match keys:  host + domain (composite — uniquely identifies the FQDN)
Entity suffix: Host (searchHost, getHost, addHost, setHost, delHost, toggleHost)

Endpoints:
    search  POST dnsmasq/settings/searchHost
    get     GET  dnsmasq/settings/getHost/{uuid}
    create  POST dnsmasq/settings/addHost
    update  POST dnsmasq/settings/setHost/{uuid}
    delete  POST dnsmasq/settings/delHost/{uuid}
    toggle  POST dnsmasq/settings/toggleHost/{uuid}/{enabled}
    apply   POST dnsmasq/service/reconfigure

Redact fields: none
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DnsmasqHostManager(BaseManager):
    """Manage OPNsense Dnsmasq host entries via /api/dnsmasq/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. Identity is the
    ``host``+``domain`` composite — together they form the FQDN. Multiple
    entries can legitimately share a domain (different hostnames) or a host
    (different domains), so the composite is required.

    Pure DHCP-only reservations (no FQDN) are out of the primary use case —
    if you need them, set ``host`` to a unique synthetic name (e.g.
    ``'reservation-<mac-slug>'``) so the composite key remains unique.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnsmasqHostManager(client)
            await mgr.ensure("present", {
                "host": "printer-01",
                "domain": "lan.example.com",
                "ip": "10.0.0.50",
                "descr": "office printer",
            })

    Input (ensure present):
        host:       Short hostname (required, part of identity).
        domain:     Domain (required, part of identity).
        local:      ``'0'`` | ``'1'`` (optional).
        ip:         IPv4 or IPv6 string (optional — required for DNS or DHCP).
        cnames:     CSV of CNAME aliases (optional).
        client_id:  DHCP client-id string (optional).
        hwaddr:     MAC address for DHCP reservation (optional).
        lease_time: e.g. ``'12h'`` (optional).
        ignore:     ``'0'`` | ``'1'`` (optional).
        set_tag:    DHCP tag UUID (optional).
        descr:      Free-text description (optional).
        comments:   Multi-line comments (optional).
        aliases:    Additional alias names (optional).

    Output (EnsureResult):
        changed:  bool — True if state was modified.
        action:   'created' | 'updated' | 'deleted' | 'noop'.
        uuid:     Resource UUID (None on noop absent).
        before:   Previous state dict.
        after:    New state dict.
    """

    _endpoint = "dnsmasq/settings"
    _payload_key = "host"
    _entity_suffix = "Host"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["host", "domain"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "host": {"type": "str", "required": True, "max_length": 255},
        "domain": {"type": "str", "required": True, "max_length": 255},
        "local": {"type": "bool_str"},
        "ip": {"type": "str", "max_length": 255},
        "cnames": {"type": "str", "max_length": 1024},
        "client_id": {"type": "str", "max_length": 255},
        "hwaddr": {"type": "str", "max_length": 64},
        "lease_time": {"type": "str", "max_length": 32},
        "ignore": {"type": "bool_str"},
        "set_tag": {"type": "str", "max_length": 64},
        "descr": {"type": "str", "max_length": 1024},
        "comments": {"type": "str", "max_length": 4096},
        "aliases": {"type": "str", "max_length": 1024},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq host manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
