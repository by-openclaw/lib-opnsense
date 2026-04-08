# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv6 subnet manager — CRUD + ensure() for DHCPv6 subnets.

API domain: /api/kea/dhcpv6
Payload key: subnet6
Match key:   subnet (unique subnet CIDR)
Entity suffix: Subnet (searchSubnet, getSubnet, addSubnet, setSubnet, delSubnet)

Endpoints:
    search  GET  kea/dhcpv6/searchSubnet
    get     GET  kea/dhcpv6/getSubnet/{uuid}
    create  POST kea/dhcpv6/addSubnet
    update  POST kea/dhcpv6/setSubnet/{uuid}
    delete  POST kea/dhcpv6/delSubnet/{uuid}
    apply   POST kea/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class Kea6SubnetManager(BaseManager):
    """Manage OPNsense Kea DHCPv6 subnets via /api/kea/dhcpv6.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DHCPv6 subnets define address pools for IPv6 DHCP allocation.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = Kea6SubnetManager(client)
            result = await mgr.ensure("present", {
                "subnet": "2001:db8::/64",
                "description": "IPv6 LAN pool",
            })
    """

    _endpoint = "kea/dhcpv6"
    _payload_key = "subnet6"
    _entity_suffix = "Subnet"
    _apply_endpoint = "kea/service/reconfigure"
    _apply_timeout = 60
    _match_key = "subnet"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "subnet": {"type": "str", "required": True, "max_length": 255},
        "interface": {"type": "str", "required": True},
        "description": {"type": "str", "max_length": 255},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Kea DHCPv6 subnet manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
