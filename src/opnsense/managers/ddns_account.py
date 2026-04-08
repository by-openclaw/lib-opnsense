# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense DynDNS account manager — CRUD + ensure().

API domain: /api/dyndns/accounts
Payload key: account
Match key:   description (unique account description)
Entity suffix: Item (getItem, addItem, setItem, delItem)

Endpoints:
    search  GET  dyndns/accounts/searchItem  (standard)
    get     GET  dyndns/accounts/getItem/{uuid}
    create  POST dyndns/accounts/addItem
    update  POST dyndns/accounts/setItem/{uuid}
    delete  POST dyndns/accounts/delItem/{uuid}
    apply   POST dyndns/service/reconfigure

Redact fields: password
Logging: inherits BaseManager contract (see base.py docstring)
Safety:  see docs/test-zone-plan.md

Note: DynDNS is built-in on OPNsense 26.1 (not the os-ddclient plugin).
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class DdnsAccountManager(BaseManager):
    """Manage OPNsense DynDNS accounts via /api/dyndns/accounts.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DynDNS accounts define dynamic DNS update configurations for
    automatic IP address registration with DNS providers.

    Note: DynDNS is built-in on OPNsense 26.1 (not the os-ddclient plugin).
    Note: service "cloudflare" for Cloudflare DNS updates.
    Note: password redacted in results.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DdnsAccountManager(client)
            result = await mgr.ensure("present", {
                "description": "Cloudflare DDNS",
                "service": "cloudflare",
                "username": "user@example.com",
                "password": "api-token",
                "zone": "example.com",
                "enabled": "1",
            })

    Input (ensure present):
        description:      Account description, max 255 (required)
        enabled:          Enable account (optional, default='1')
        service:          DynDNS provider — e.g. 'cloudflare', 'aws', 'custom', 'desec-v4'
        protocol:         Protocol identifier (optional)
        server:           Server hostname (optional)
        username:         Authentication username (optional)
        password:         Authentication password (optional, redacted in output)
        resourceId:       Resource identifier, e.g. zone ID (optional)
        zone:             DNS zone (optional)
        wildcard:         Enable wildcard (optional, default='0')
        checkip:          IP check method (optional, default='web_cloudflare')
        checkip_timeout:  IP check timeout in seconds, min 1 (optional, default='10')
        force_ssl:        Force SSL (optional, default='1')
        ttl:              TTL in seconds, min 60 (optional, default='300')
        interface:        Network interface (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "dyndns/accounts"
    _payload_key = "account"
    _entity_suffix = "Item"
    _apply_endpoint = "dyndns/service/reconfigure"
    _apply_timeout = 30
    _match_keys = ["description"]

    REDACT_FIELDS: set[str] = {"password"}

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "enabled": {"type": "bool_str"},
        "service": {"type": "str"},
        "protocol": {"type": "str"},
        "server": {"type": "str"},
        "username": {"type": "str"},
        "password": {"type": "str"},
        "resourceId": {"type": "str"},
        "hostnames": {"type": "str", "required": True},
        "zone": {"type": "str"},
        "wildcard": {"type": "bool_str"},
        "checkip": {"type": "str", "required": True},
        "checkip_timeout": {"type": "int", "min": 1},
        "force_ssl": {"type": "bool_str"},
        "ttl": {"type": "int", "min": 60},
        "interface": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the DynDNS account manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
