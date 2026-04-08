# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense OpenVPN instance manager -- CRUD + ensure().

API domain: /api/openvpn/instances
Payload key: instance
Match key:   description (unique instance description)
Entity suffix: '' (bare: get, search, add, set, del)

Endpoints:
    search  GET  openvpn/instances/search
    get     GET  openvpn/instances/get/{uuid}
    create  POST openvpn/instances/add
    update  POST openvpn/instances/set/{uuid}
    delete  POST openvpn/instances/del/{uuid}
    apply   POST openvpn/service/reconfigure

Redact fields: password, auth-gen-token-secret
Logging: inherits BaseManager contract (see base.py docstring)
"""

from __future__ import annotations

import logging

from opnsense.client import OpnsenseClient
from opnsense.managers.base import BaseManager

logger = logging.getLogger(__name__)


class OvpnInstanceManager(BaseManager):
    """Manage OPNsense OpenVPN instances via /api/openvpn/instances.

    Inherits full CRUD + ensure() lifecycle from BaseManager.
    OpenVPN instances define VPN server or client endpoints.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = OvpnInstanceManager(client)
            result = await mgr.ensure("present", {
                "description": "office-vpn",
                "role": "server",
                "proto": "udp",
                "port": "1194",
                "server": "10.8.0.0/24",
                "cert": "<refid>",
                "ca": "<refid>",
            })

    Input (ensure present):
        description:        Instance description, max 255 (required, match key)
        enabled:            Enable instance ('0' or '1', optional, default='1')
        role:               Instance role ('server' or 'client', optional, default='server')
        dev_type:           Device type (optional, default='tun')
        proto:              Protocol (optional, default='udp')
        port:               Listen/connect port 1-65535 (optional)
        server:             Tunnel network CIDR, e.g. '10.8.0.0/24' (optional)
        server_ipv6:        IPv6 tunnel network CIDR (optional)
        cert:               Certificate refid -- NOT a UUID (optional)
        ca:                 CA refid -- NOT a UUID (optional)
        auth:               Authentication algorithm (optional)
        topology:           Topology: 'subnet', 'net30', 'p2p' (optional, default='subnet')
        local:              Bind address (optional)
        remote:             Remote address for client mode (optional)
        keepalive_interval: Keepalive interval in seconds (optional)
        keepalive_timeout:  Keepalive timeout in seconds (optional)
        tun_mtu:            Tunnel MTU (optional)
        maxclients:         Maximum concurrent clients (optional)
        redirect_gateway:   Redirect gateway flags (optional)
        username:           Username for client auth (optional)
        password:           Password for client auth (optional, redacted)

    Note: ``cert`` and ``ca`` accept OPNsense certificate *refid* values,
    not UUIDs. Obtain refids from the Trust CA / Trust Cert managers or
    the OPNsense web UI.

    REDACT_FIELDS: password, auth-gen-token-secret -- never exposed in
    before/after dicts.

    Output (EnsureResult):
        changed:  bool -- True if state was modified
        action:   'created' | 'updated' | 'deleted' | 'noop'
        uuid:     Resource UUID (None on noop absent)
        before:   Previous state dict (redacted)
        after:    New state dict (redacted)
    """

    _endpoint = "openvpn/instances"
    _payload_key = "instance"
    _entity_suffix = ""
    _apply_endpoint = "openvpn/service/reconfigure"
    _apply_timeout = 30
    _match_key = "description"

    REDACT_FIELDS: set[str] = {"password", "auth-gen-token-secret"}

    _validators = {
        "description": {"type": "str", "required": True, "max_length": 255},
        "vpnid": {"type": "str"},
        "enabled": {"type": "bool_str"},
        "role": {"type": "enum", "values": ["server", "client"]},
        "dev_type": {"type": "str"},
        "proto": {"type": "str"},
        "port": {"type": "port"},
        "server": {"type": "str"},
        "server_ipv6": {"type": "str"},
        "cert": {"type": "str"},
        "ca": {"type": "str"},
        "auth": {"type": "str"},
        "topology": {"type": "str"},
        "local": {"type": "str"},
        "remote": {"type": "str"},
        "keepalive_interval": {"type": "str"},
        "keepalive_timeout": {"type": "str"},
        "tun_mtu": {"type": "str"},
        "maxclients": {"type": "str"},
        "redirect_gateway": {"type": "str"},
        "username": {"type": "str"},
        "password": {"type": "str"},
    }

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the OpenVPN instance manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
