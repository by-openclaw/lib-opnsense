# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCPv4 HA peer manager — CRUD + ensure() for DHCP HA peers.

API domain: /api/kea/dhcpv4
Payload key: peer
Match key:   name (unique peer name)
Entity suffix: Peer (searchPeer, getPeer, addPeer, setPeer, delPeer)

Endpoints:
    search  GET  kea/dhcpv4/searchPeer
    get     GET  kea/dhcpv4/getPeer/{uuid}
    create  POST kea/dhcpv4/addPeer
    update  POST kea/dhcpv4/setPeer/{uuid}
    delete  POST kea/dhcpv4/delPeer/{uuid}
    apply   POST kea/service/reconfigure

Redact fields: none
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager


class Kea4PeerManager(BaseManager):
    """Manage OPNsense Kea DHCPv4 HA peers via /api/kea/dhcpv4.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    DHCPv4 peers define HA replication partners for DHCP failover.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = Kea4PeerManager(client)
            result = await mgr.ensure("present", {
                "name": "peer-standby",
                "role": "primary",
                "url": "https://peer.example.com:8000/",
            })
    """

    _endpoint = "kea/dhcpv4"
    _payload_key = "peer"
    _entity_suffix = "Peer"
    _apply_endpoint = "kea/service/reconfigure"
    _apply_timeout = 60
    _match_key = "name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "name": {"type": "str", "required": True, "max_length": 255},
        "role": {"type": "enum", "values": ["primary", "standby"]},
        "url": {"type": "str", "required": True},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Kea DHCPv4 HA peer manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
