# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound DNS access control list model — typed frozen dataclass.

Maps to OPNsense API: ``/api/unbound/settings``
Payload key: ``acl``
Match key: ``name``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UbAcl:
    """Unbound DNS access control list entity from OPNsense unbound/settings API.

    Attributes:
        name:        ACL name (required, unique).
        action:      ACL action ('allow', 'deny', 'refuse', etc.).
        networks:    Comma-separated list of networks.
        enabled:     Whether the ACL is enabled ('0' or '1').
        description: Human-readable description.
        uuid:        Resource UUID assigned by OPNsense.
    """

    name: str
    action: str = "allow"
    networks: str = ""
    enabled: str = "1"
    description: str = ""
    uuid: str = ""
