# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense captive portal zone model — typed frozen dataclass.

Maps to OPNsense API: ``/api/captiveportal/settings``
Payload key: ``zone``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CpZone:
    """Captive portal zone entity from OPNsense captiveportal/settings API.

    Attributes:
        description:      Zone description (required).
        enabled:          Whether the zone is enabled ('0' or '1').
        interfaces:       Comma-separated interface names.
        authservers:      Authentication server references.
        idletimeout:      Idle timeout in seconds.
        hardtimeout:      Hard timeout in seconds.
        concurrentlogins: Allow concurrent logins ('0' or '1').
        certificate:      TLS certificate UUID.
        servername:       Server name for portal.
        uuid:             Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    interfaces: str = ""
    authservers: str = ""
    idletimeout: str = "0"
    hardtimeout: str = "0"
    concurrentlogins: str = "1"
    certificate: str = ""
    servername: str = ""
    uuid: str = ""
