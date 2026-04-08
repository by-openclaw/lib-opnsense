# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS access control list manager — CRUD + ensure().

API domain: /api/unbound/settings
Payload key: acl
Match key:   name (unique ACL name)
Entity suffix: Acl (searchAcl, getAcl, etc.)

Endpoints:
    search  GET  unbound/settings/searchAcl
    get     GET  unbound/settings/getAcl/{uuid}
    create  POST unbound/settings/addAcl
    update  POST unbound/settings/setAcl/{uuid}
    delete  POST unbound/settings/delAcl/{uuid}
    apply   POST unbound/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class UbAclManager(BaseManager):
    """Manage OPNsense Unbound DNS access control lists via /api/unbound/settings.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    ACLs control which networks are allowed to query the local DNS resolver.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbAclManager(client)
            result = await mgr.ensure("present", {
                "name": "lan-access",
                "action": "allow",
                "networks": "10.0.0.0/8",
            })
    """

    _endpoint = "unbound/settings"
    _payload_key = "acl"
    _entity_suffix = "Acl"
    _apply_endpoint = "unbound/service/reconfigure"
    _apply_timeout = 60
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "action": {
            "type": "enum",
            "values": [
                "allow",
                "deny",
                "refuse",
                "allow_snoop",
                "deny_non_local",
                "refuse_non_local",
            ],
        },
        "networks": {"type": "str"},
        "enabled": {"type": "bool_str"},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound ACL manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
