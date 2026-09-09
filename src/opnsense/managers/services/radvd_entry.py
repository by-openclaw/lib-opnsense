# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense radvd entry manager — per-interface IPv6 RA config CRUD + ensure().

API domain: /api/radvd/settings
Payload key: entries (plural — verified via probe; URL suffix is singular ``Entry``)
Match key:   interface (unique slot id, one RA entry per interface)
Entity suffix: Entry (searchEntry, getEntry, addEntry, setEntry, delEntry)

Endpoints:
    search  POST radvd/settings/searchEntry
    get     GET  radvd/settings/getEntry/{uuid}
    create  POST radvd/settings/addEntry
    update  POST radvd/settings/setEntry/{uuid}
    delete  POST radvd/settings/delEntry/{uuid}
    apply   POST radvd/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)

Reference: https://docs.opnsense.org/manual/router_advertisements.html
"""

from __future__ import annotations

from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class RadvdEntryManager(BaseManager):
    """Manage OPNsense radvd per-interface RA entries via /api/radvd/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager. Identity is the
    OPNsense interface slot — at most one RA config per interface.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = RadvdEntryManager(client)
            result = await mgr.ensure("present", {
                "interface": "opt2",
                "enabled": "1",
                "mode": "managed",          # use Kea/DHCPv6 for addresses
            })

    Input (ensure present):
        interface:       Interface slot id (required, e.g. ``'opt2'``).
        enabled:         ``'0'`` | ``'1'`` (default ``'1'``).
        Base6Interface:  Slot providing the prefix (optional, ``''`` = static).
        mode:            ``'router'`` | ``'unmanaged'`` | ``'managed'`` |
                         ``'assist'`` | ``'stateless'`` (default ``'stateless'``).
        DeprecatePrefix: ``''`` | ``'on'`` | ``'off'``.
        RemoveAdvOnExit: ``''`` | ``'on'`` | ``'off'``.
        RemoveRoute:     ``''`` | ``'on'`` | ``'off'``.

    Output (EnsureResult):
        changed:  bool — True if state was modified.
        action:   'created' | 'updated' | 'deleted' | 'noop'.
        uuid:     Resource UUID (None on noop absent).
        before:   Previous state dict.
        after:    New state dict.
    """

    _endpoint = "radvd/settings"
    # Body wrapper is plural ("entries") even though the URL suffix is singular
    # ("Entry") — verified on OPNsense 26.1 via probe.
    _payload_key = "entries"
    _entity_suffix = "Entry"
    _apply_endpoint = "radvd/service/reconfigure"
    _apply_timeout = 30
    _match_keys = ["interface"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "interface": {"type": "str", "required": True, "max_length": 32},
        "enabled": {"type": "bool_str"},
        "Base6Interface": {"type": "str", "max_length": 32},
        "mode": {
            "type": "enum",
            "values": ["router", "unmanaged", "managed", "assist", "stateless"],
        },
        "DeprecatePrefix": {"type": "enum", "values": ["", "on", "off"]},
        "RemoveAdvOnExit": {"type": "enum", "values": ["", "on", "off"]},
        "RemoveRoute": {"type": "enum", "values": ["", "on", "off"]},
        # Resolver advertisement (RFC 8106). ``dns`` is the plugin's "advertise DNS"
        # toggle: with it on and ``RDNSS`` EMPTY, radvd advertises the interface's own
        # address, so IPv6 clients resolve at the firewall no matter what the DHCPv4
        # options say. Set ``RDNSS`` to advertise a specific resolver instead — that is
        # the only way to give IPv6 clients the same resolver as IPv4.
        "dns": {"type": "bool_str"},
        "RDNSS": {"type": "csv_ip", "version": 6, "max_items": 3},  # RFC 8106 caps at 3
        "DNSSL": {"type": "str", "max_length": 255},
        "AdvRDNSSLifetime": {"type": "str", "max_length": 16},
        "AdvDNSSLLifetime": {"type": "str", "max_length": 16},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the radvd entry manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def list(self, search_phrase: str = "") -> list[dict[str, Any]]:
        """List radvd entries.

        Overrides the base ``list`` to ignore ``search_phrase``: OPNsense's
        ``searchEntry`` filters against the human-readable display value
        (``%interface``, e.g. ``OOB_MGMT``), not the slot id (``lan``) that
        we match on. Passing ``lan`` as a search phrase yields zero hits and
        breaks ``find_existing``. Total entry count is bounded by the number
        of interfaces (~13), so unconditional enumeration is cheap.
        """
        return await self._client.search(self._endpoints.search(), search_phrase="")
