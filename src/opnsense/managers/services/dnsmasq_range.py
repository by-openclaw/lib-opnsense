# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq DHCP range manager — DHCPv4 / DHCPv6 pool CRUD + ensure().

API domain: /api/dnsmasq/settings
Payload key: range
Match keys:  interface + start_addr (composite — uniquely identifies a pool)
Entity suffix: Range (searchRange, getRange, addRange, setRange, delRange, toggleRange)

Endpoints:
    search  POST dnsmasq/settings/searchRange
    get     GET  dnsmasq/settings/getRange/{uuid}
    create  POST dnsmasq/settings/addRange
    update  POST dnsmasq/settings/setRange/{uuid}
    delete  POST dnsmasq/settings/delRange/{uuid}
    toggle  POST dnsmasq/settings/toggleRange/{uuid}/{enabled}
    apply   POST dnsmasq/service/reconfigure

IPv4 vs IPv6 (verified via probe):
  * **IPv4** range — send ``subnet_mask`` (dotted) + ``start_addr`` + ``end_addr``.
    Do NOT set ``constructor`` or ``prefix_len``.
  * **IPv6** range — send ``constructor`` (slot id providing the prefix) +
    ``prefix_len`` + ``start_addr``/``end_addr`` as partial addresses
    (``'::1000'``). May also carry RA options (``ra_mode``, ``ra_priority``, ...).

Redact fields: none
Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DnsmasqRangeManager(BaseManager):
    """Manage OPNsense Dnsmasq DHCP4/DHCP6 ranges via /api/dnsmasq/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. Identity is the
    ``interface``+``start_addr`` composite — at most one range per interface
    starting at a given address. Multiple ranges on the same interface (with
    different start addresses) are allowed.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnsmasqRangeManager(client)
            # IPv4 pool
            await mgr.ensure("present", {
                "interface": "lan",
                "subnet_mask": "255.255.255.0",
                "start_addr": "10.0.0.100",
                "end_addr": "10.0.0.200",
                "lease_time": "7200",  # integer seconds (2h)
            })
            # IPv6 pool driven by SLAAC prefix from the same interface
            await mgr.ensure("present", {
                "interface": "lan",
                "constructor": "lan",
                "prefix_len": "64",
                "start_addr": "::1000",
                "end_addr": "::2000",
                "ra_mode": "slaac",
            })

    Input (ensure present) — see :class:`opnsense.models.services.dnsmasq_range.DnsmasqRange`
    for the full attribute list.

    Output (EnsureResult):
        changed:  bool — True if state was modified.
        action:   'created' | 'updated' | 'deleted' | 'noop'.
        uuid:     Resource UUID (None on noop absent).
        before:   Previous state dict.
        after:    New state dict.
    """

    _endpoint = "dnsmasq/settings"
    _payload_key = "range"
    _entity_suffix = "Range"
    _apply_endpoint = "dnsmasq/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["interface", "start_addr"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "interface": {"type": "str", "required": True, "max_length": 32},
        "set_tag": {"type": "str", "max_length": 64},
        "start_addr": {"type": "str", "required": True, "max_length": 128},
        "end_addr": {"type": "str", "max_length": 128},
        "subnet_mask": {"type": "str", "max_length": 16},
        "constructor": {"type": "str", "max_length": 32},
        "mode": {"type": "str", "max_length": 64},
        "prefix_len": {"type": "str", "max_length": 4},
        "lease_time": {"type": "str", "max_length": 16},
        "domain_type": {
            "type": "enum",
            "values": ["", "range", "interface"],
        },
        "domain": {"type": "str", "max_length": 255},
        "nosync": {"type": "bool_str"},
        "ra_mode": {
            "type": "enum",
            "values": [
                "",
                "slaac",
                "ra-stateless",
                "ra-names",
                "ra-only",
                "ra-advrouter",
                "off-link",
            ],
        },
        "ra_priority": {
            "type": "enum",
            "values": ["", "low", "medium", "high"],
        },
        "ra_mtu": {"type": "str", "max_length": 6},
        "ra_interval": {"type": "str", "max_length": 6},
        "ra_router_lifetime": {"type": "str", "max_length": 6},
        "description": {"type": "str", "max_length": 1024},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq range manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List ranges.

        Overrides the base ``list`` to ignore ``search_phrase`` — OPNsense's
        ``searchRange`` filters against the ``%interface`` display value
        (``'OOB_MGMT'``), not the slot id (``'lan'``) we match on. Same
        footgun as :class:`RadvdEntryManager`. Range count is small in
        practice (~one per VLAN), so unconditional enumeration is cheap.
        """
        return await self._client.search(self._endpoints.search(), search_phrase="")
