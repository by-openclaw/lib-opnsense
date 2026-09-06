# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
r"""OpenVPN client-specific override (CSO) manager — CRUD + ensure().

DRAFT / BLOCKED: /api/openvpn/clientoverwrites/* returns 404 on the 26.7 CE nano
test build — the controller exists in source but the route is not live, so this
manager cannot be integration-tested yet. Verify on a full/DVD 26.7 install
before enabling or merging (lib rule: no merge without integration tests).

API domain: /api/openvpn/clientoverwrites
Payload key: cso
Match key:   common_name (the client certificate CN the override applies to)
Entity suffix: '' (bare: search, get, add, set, del, toggle)
Endpoints:
    search  GET  openvpn/clientoverwrites/search
    get     GET  openvpn/clientoverwrites/get/{uuid}
    create  POST openvpn/clientoverwrites/add
    update  POST openvpn/clientoverwrites/set/{uuid}
    delete  POST openvpn/clientoverwrites/del/{uuid}
    toggle  POST openvpn/clientoverwrites/toggle/{uuid}
    apply   POST openvpn/service/reconfigure   (CSOs apply via the OpenVPN service)

Model: OPNsense\\OpenVPN\\OpenVPN, node <Overwrite> (internalModelName 'cso').
Verified against a live OPNsense 26.7 test FW (route + schema discovery).
Logging: inherits BaseManager contract (see base.py docstring).
"""

from __future__ import annotations

from opnsense.managers.base import BaseManager


class OvpnClientOverwriteManager(BaseManager):
    """Manage OpenVPN client-specific overrides via /api/openvpn/clientoverwrites.

    A client-specific override (CSO) pins per-client settings — pushed routes,
    DNS, a fixed tunnel address — keyed on the client certificate common name.
    Inherits full CRUD + ensure() lifecycle from BaseManager.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = OvpnClientOverwriteManager(client)
            await mgr.ensure("present", {
                "common_name": "road-warrior-01",
                "servers": "<instance-uuid>",
                "tunnel_network": "10.8.0.16/30",
                "push_reset": "1",
                "remote_networks": "10.1.0.0/16",
                "description": "Ops laptop — full-tunnel",
            })

    Input (ensure present):
        common_name:      Client certificate CN this override matches (required)
        servers:          OpenVPN instance UUID(s) the override applies to
        enabled:          '1' | '0'
        block:            '1' to block the client entirely
        push_reset:       '1' to not push server-wide options to this client
        tunnel_network:   Fixed tunnel address/subnet for this client
        local_networks:   Networks reachable behind the server, pushed to client
        remote_networks:  Networks behind THIS client (iroute)
        route_gateway:    Gateway for the pushed routes
        redirect_gateway: Redirect-gateway option
        register_dns:     '1' to push register-dns (Windows)
        dns_domain:       DNS domain to push
        dns_domain_search: DNS search domains
        dns_servers:      DNS servers to push
        ntp_servers:      NTP servers to push
        wins_servers:     WINS servers to push
        description:      Free-text note

    Output (EnsureResult): changed, action, uuid, before, after.
    """

    _endpoint = "openvpn/clientoverwrites"
    _payload_key = "cso"
    _entity_suffix = ""  # bare action names: search, get, add, set, del, toggle
    _apply_endpoint = "openvpn/service/reconfigure"
    _match_key = "common_name"

    REDACT_FIELDS: set[str] = set()

    _validators = {
        "common_name": {"type": "str", "required": True, "max_length": 255},
        "servers": {"type": "str"},
        "enabled": {"type": "bool_str"},
        "block": {"type": "bool_str"},
        "push_reset": {"type": "bool_str"},
        "tunnel_network": {"type": "str"},
        "local_networks": {"type": "str"},
        "remote_networks": {"type": "str"},
        "route_gateway": {"type": "str"},
        "redirect_gateway": {"type": "str"},
        "register_dns": {"type": "bool_str"},
        "dns_domain": {"type": "str"},
        "dns_domain_search": {"type": "str"},
        "dns_servers": {"type": "str"},
        "ntp_servers": {"type": "str"},
        "wins_servers": {"type": "str"},
        "description": {"type": "str", "max_length": 255},
    }
