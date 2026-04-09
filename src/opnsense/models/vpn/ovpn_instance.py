# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense OpenVPN instance model -- typed frozen dataclass.

Maps to OPNsense API: ``/api/openvpn/instances``
Payload key: ``instance``
Match key: ``description``

Note: ``cert`` and ``ca`` fields use OPNsense certificate *refid* values,
not UUIDs.  Obtain refids via the Trust CA / Trust Cert managers or the
OPNsense web UI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OvpnInstance:
    """OpenVPN instance entity from OPNsense openvpn/instances API.

    Attributes:
        description:        Instance description (required, match key).
        enabled:            Whether the instance is enabled ('0' or '1').
        role:               Instance role ('server' or 'client').
        dev_type:           Device type (e.g. 'tun', 'tap').
        proto:              Protocol (e.g. 'udp', 'tcp').
        port:               Listen/connect port.
        server:             Tunnel network CIDR (e.g. '10.8.0.0/24').
        server_ipv6:        IPv6 tunnel network CIDR.
        cert:               Certificate refid (not UUID).
        ca:                 CA refid (not UUID).
        auth:               Authentication algorithm.
        topology:           Topology ('subnet', 'net30', 'p2p').
        local:              Bind address.
        remote:             Remote address (client mode).
        keepalive_interval: Keepalive interval seconds.
        keepalive_timeout:  Keepalive timeout seconds.
        tun_mtu:            Tunnel MTU.
        maxclients:         Maximum concurrent clients.
        redirect_gateway:   Redirect gateway flags.
        username:           Username (client auth).
        password:           Password (client auth, redacted in output).
        uuid:               Resource UUID assigned by OPNsense.
    """

    description: str
    vpnid: str = ""
    enabled: str = "1"
    role: str = "server"
    dev_type: str = "tun"
    proto: str = "udp"
    port: str = ""
    server: str = ""
    server_ipv6: str = ""
    cert: str = ""
    ca: str = ""
    auth: str = ""
    topology: str = "subnet"
    local: str = ""
    remote: str = ""
    keepalive_interval: str = ""
    keepalive_timeout: str = ""
    tun_mtu: str = ""
    maxclients: str = ""
    redirect_gateway: str = ""
    username: str = ""
    password: str = ""
    uuid: str = ""
