# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS host alias manager — create + read only.

API domain: /api/unbound/settings
Payload key: alias
Match keys:  ['hostname', 'domain']
Entity suffix: HostAlias (searchHostAlias, getHostAlias, addHostAlias)

Endpoints:
    search  POST unbound/settings/searchHostAlias
    get     GET  unbound/settings/getHostAlias/{uuid}
    create  POST unbound/settings/addHostAlias
    set     404 — NOT AVAILABLE on OPNsense 26.1.5
    del     404 — NOT AVAILABLE on OPNsense 26.1.5
    apply   POST unbound/service/reconfigure

LIMITATION: OPNsense 26.1.5 does not expose setHostAlias or delHostAlias
endpoints. This manager supports create + read only. Update and delete
will raise OpnsenseEndpointMissingError (404) if called.

The 'host' field references the parent HostOverride UUID.

Safety: see docs/test-zone-plan.md §2.11
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbHostAliasManager(BaseManager):
    """Manage Unbound DNS host aliases via /api/unbound/settings.

    Host aliases are CNAME-like records attached to a parent host override.
    Requires the parent HostOverride UUID in the 'host' field.

    LIMITATION: update (set) and delete (del) are NOT available on
    OPNsense 26.1.5. Only create + read are supported.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbHostAliasManager(client)
            result = await mgr.ensure("present", {
                "host": "<parent-host-override-uuid>",
                "hostname": "web-alias",
                "domain": "lab.test",
                "description": "inttest-alias",
            })
    """

    _endpoint = "unbound/settings"
    _payload_key = "alias"
    _entity_suffix = "HostAlias"
    _apply_endpoint = "unbound/service/reconfigure"
    _apply_timeout = 60
    _match_keys = ["hostname", "domain"]

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "hostname": {"type": "str", "required": True, "max_length": 255},
        "domain": {"type": "str", "max_length": 255},
        "host": {"type": "str"},
        "enabled": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound host alias manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
