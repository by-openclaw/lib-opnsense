# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense syslog destination model — typed frozen dataclass.

Maps to OPNsense API: ``/api/syslog/settings``
Payload key: ``destination``
Match key: ``description``
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyslogDest:
    """Syslog destination entity from OPNsense syslog/settings API.

    Attributes:
        description:  Destination description (required, max 255).
        enabled:      Whether the destination is enabled ('0' or '1').
        transport:    Transport protocol ('udp4', 'tcp4', 'udp6', 'tcp6').
        program:      Filter by program name.
        level:        Comma-separated log levels.
        facility:     Comma-separated facilities.
        hostname:     Target hostname or IP (required, max 255).
        port:         Target port number.
        rfc5424:      Use RFC 5424 format ('0' or '1').
        certificate:  TLS certificate reference.
        uuid:         Resource UUID assigned by OPNsense.
    """

    description: str
    enabled: str = "1"
    transport: str = "udp4"
    program: str = ""
    level: str = ""
    facility: str = ""
    hostname: str = ""
    port: str = "514"
    rfc5424: str = "0"
    certificate: str = ""
    uuid: str = ""
