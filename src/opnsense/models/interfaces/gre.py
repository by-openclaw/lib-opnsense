# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense interface GRE tunnel model — typed frozen dataclass.

Maps to OPNsense API: ``/api/interfaces/gre_settings``
Payload key: ``gre``
Match keys: ``['tunnel-local-addr', 'tunnel-remote-addr']``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IfGre:
    """GRE tunnel interface entity from OPNsense interfaces/gre_settings API.

    Attributes:
        tunnel_local_addr:  Local tunnel endpoint (required).
        tunnel_remote_addr: Remote tunnel endpoint.
        tunnel_remote_net:  Remote network prefix length.
        descr:              Description (max 255).
        uuid:               Resource UUID assigned by OPNsense.
    """

    tunnel_local_addr: str
    tunnel_remote_addr: str = ""
    tunnel_remote_net: str = "32"
    descr: str = ""
    uuid: str = ""
