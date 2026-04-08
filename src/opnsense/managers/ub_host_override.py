# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS host override manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: host
Match keys:  ['hostname', 'domain', 'server']
Entity suffix: HostOverride (searchHostOverride, getHostOverride, etc.)

Endpoints:
    search  GET  unbound/settings/searchHostOverride
    get     GET  unbound/settings/getHostOverride/{uuid}
    create  POST unbound/settings/addHostOverride
    update  POST unbound/settings/setHostOverride/{uuid}
    delete  POST unbound/settings/delHostOverride/{uuid}
    apply   POST unbound/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbHostOverrideManager(BaseManager):
    """Manage OPNsense Unbound DNS host overrides via /api/unbound/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    Host overrides map hostnames to IP addresses in the local DNS resolver.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbHostOverrideManager(client)
            result = await mgr.ensure("present", {
                "hostname": "ns1",
                "domain": "example.com",
                "server": "10.0.0.1",
                "rr": "A",
            })
    """

    _endpoint = "unbound/settings"
    _payload_key = "host"
    _entity_suffix = "HostOverride"
    _apply_endpoint = "unbound/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["hostname", "domain", "server"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "hostname": {"type": "str", "required": True, "max_length": 255},
        "domain": {"type": "str", "max_length": 255},
        "server": {"type": "str", "max_length": 255},
        "rr": {"type": "enum", "values": ["A", "AAAA", "MX", "TXT"]},
        "mxprio": {"type": "str"},
        "mx": {"type": "str"},
        "ttl": {"type": "str"},
        "txtdata": {"type": "str"},
        "addptr": {"type": "bool_str"},
        "enabled": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound host override manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
