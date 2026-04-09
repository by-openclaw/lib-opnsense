# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 subnet manager — CRUD + ensure() for DHCPv4 subnets.

API domain: /api/kea/dhcpv4
Payload key: subnet4
Match key:   subnet (unique subnet CIDR)
Entity suffix: Subnet (searchSubnet, getSubnet, addSubnet, setSubnet, delSubnet)

Endpoints:
    search  GET  kea/dhcpv4/searchSubnet
    get     GET  kea/dhcpv4/getSubnet/{uuid}
    create  POST kea/dhcpv4/addSubnet
    update  POST kea/dhcpv4/setSubnet/{uuid}
    delete  POST kea/dhcpv4/delSubnet/{uuid}
    apply   POST kea/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class Kea4SubnetManager(BaseManager):
    """Manage OPNsense Kea DHCPv4 subnets via /api/kea/dhcpv4.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DHCPv4 subnets define address pools for IPv4 DHCP allocation.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = Kea4SubnetManager(client)
            result = await mgr.ensure("present", {
                "subnet": "10.0.0.0/24",
                "pools": "10.0.0.100-10.0.0.200",
                "description": "LAN DHCP pool",
            })

    Input (ensure present):
        subnet:           Subnet CIDR, max 255 (required)
        pools:            Address pool ranges (optional)
        next_server:      TFTP/PXE next-server address (optional)
        description:      Description, max 255 (optional)
        match-client-id:  Match client ID (optional, default='1')
        ddns_forward_zone: DDNS forward zone (optional)
        ddns_dns_server:  DDNS DNS server address (optional)
        option_data:  DHCP options (optional, dict):
            domain_name_servers:    DNS servers (optional)
            domain_search:          Search domains (optional)
            routers:                Default gateway (optional)
            static_routes:          Static routes (optional)
            classless_static_route: Classless static routes (optional)
            domain_name:            Domain name (optional)
            ntp_servers:            NTP servers (optional)
            time_servers:           Time servers (optional)
            tftp_server_name:       TFTP server (optional)
            boot_file_name:         PXE boot file (optional)

    Output (EnsureResult):
        changed:  bool — True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "kea/dhcpv4"
    _payload_key = "subnet4"
    _entity_suffix = "Subnet"
    _apply_endpoint = "kea/service/reconfigure"
    _apply_timeout = 60
    _match_key = "subnet"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "subnet": {"type": "str", "required": True, "max_length": 255},
        "pools": {"type": "str"},
        "next_server": {"type": "str"},
        "description": {"type": "str", "max_length": 255},
        "match-client-id": {"type": "bool_str"},
        "ddns_forward_zone": {"type": "str"},
        "ddns_dns_server": {"type": "str"},
        "option_data": {
            "type": "dict",
            "fields": {
                "domain_name_servers": {"type": "str"},
                "domain_search": {"type": "str"},
                "routers": {"type": "str"},
                "static_routes": {"type": "str"},
                "classless_static_route": {"type": "str"},
                "domain_name": {"type": "str"},
                "ntp_servers": {"type": "str"},
                "time_servers": {"type": "str"},
                "tftp_server_name": {"type": "str"},
                "boot_file_name": {"type": "str"},
            },
        },
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Kea DHCPv4 subnet manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
