# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firewall alias manager — CRUD + ensure() for aliases.

API domain: /api/firewall/alias
Payload key: alias
Match key:   name (unique alias name)
Entity suffix: Item (searchItem, getItem, addItem, setItem, delItem)

Endpoints:
    search  GET  firewall/alias/searchItem
    get     GET  firewall/alias/getItem/{uuid}
    create  POST firewall/alias/addItem
    update  POST firewall/alias/setItem/{uuid}
    delete  POST firewall/alias/delItem/{uuid}
    apply   POST firewall/alias/reconfigure

Redact fields: password, username (URL table auth)
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md §M05
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class FwAliasManager(BaseManager):
    """Manage OPNsense firewall aliases via /api/firewall/alias.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Aliases reference hosts, networks, ports, URLs, GeoIP, etc.
    Redacts password/username fields used for URL table authentication.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = FwAliasManager(client)
            result = await mgr.ensure("present", {
                "name": "net_dmz",
                "type": "network",
                "content": "10.6.225.0/24",
                "description": "DMZ subnet",
            })

    Input (ensure present):
        name:         Alias name, alphanumeric/underscore, max 32 (required)
        type:         Alias type — host, network, port, url, urltable, urljson,
                      geoip, networkgroup, mac, asn, dynipv6host, authgroup,
                      internal, external (optional)
        content:      Alias content/values, max 10000 (optional)
        description:  Description, max 255 (optional)
        enabled:      Enable alias (optional, default='1')
        updatefreq:   URL table update frequency, max 10 (optional)
        proto:        IP protocol — IPv4, IPv6 (optional)
        categories:   Comma-separated category UUIDs (optional)
        interface:    Interface name (optional)
        username:     URL table auth username (optional)
        password:     URL table auth password (optional)
        authtype:     URL table auth type — '', Basic, Bearer, Header (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "firewall/alias"
    _payload_key = "alias"
    _entity_suffix = "Item"  # search_item, get_item, add_item, set_item, del_item
    _apply_endpoint = "firewall/alias/reconfigure"
    _match_key = "name"

    REDACT_FIELDS = {"password", "username"}

    _validators = {
        "name": {
            "type": "str",
            "required": True,
            "max_length": 32,
            "regex": r"^[a-zA-Z0-9_]+$",
        },
        "type": {
            "type": "enum",
            "values": [
                "host",
                "network",
                "port",
                "url",
                "urltable",
                "urljson",
                "geoip",
                "networkgroup",
                "mac",
                "asn",
                "dynipv6host",
                "authgroup",
                "internal",
                "external",
            ],
        },
        "content": {"type": "str", "max_length": 10000},
        "description": {"type": "str", "max_length": 255},
        "enabled": {"type": "bool_str"},
        "updatefreq": {"type": "str", "max_length": 10},
        "proto": {"type": "enum", "values": ["IPv4", "IPv6"]},
        "categories": {"type": "str"},
        "interface": {"type": "str"},
        "username": {"type": "str"},
        "password": {"type": "str"},
        "authtype": {"type": "enum", "values": ["", "Basic", "Bearer", "Header"]},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firewall alias manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
