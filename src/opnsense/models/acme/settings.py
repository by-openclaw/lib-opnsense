# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense ACME settings model — typed frozen dataclass (singleton).

Maps to OPNsense API: ``/api/acmeclient/settings`` (os-acme-client plugin)
Payload key: ``acmeclient`` (the ``settings`` block is nested under it)

The plugin-wide configuration: master enable, auto-renewal cron, ACME
environment (prod/staging), challenge ports and log level. There is exactly one
settings document — no UUID, no add/del (see ``AcmeSettingsManager``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AcmeSettings:
    """ACME plugin global settings from os-acme-client ``settings`` API.

    Attributes:
        enabled:            Master enable for the ACME client (``"1"``/``"0"``).
        autoRenewal:        Enable the auto-renewal cron (``"1"``/``"0"``).
        UpdateCron:         Cron job refid driving auto-renewal.
        environment:        ACME environment — ``""`` (default), ``prod``, ``stg``.
        challengePort:      Internal HTTP-01 challenge port.
        TLSchallengePort:   Internal TLS-ALPN-01 challenge port.
        restartTimeout:     Seconds to wait for service restarts.
        haproxyIntegration: Enable HAProxy integration (``"1"``/``"0"``).
        haproxyAclRef:      HAProxy ACL refid (HAProxy integration).
        haproxyActionRef:   HAProxy action refid.
        haproxyServerRef:   HAProxy server refid.
        haproxyBackendRef:  HAProxy backend refid.
        logLevel:           ``normal`` / ``extended`` / ``debug`` / ``debug2`` /
                            ``debug3``.
        showIntro:          Show the GUI intro panel (``"1"``/``"0"``).
    """

    enabled: str = "0"
    autoRenewal: str = "1"
    UpdateCron: str = ""
    environment: str = ""
    challengePort: str = "43580"
    TLSchallengePort: str = "43581"
    restartTimeout: str = "600"
    haproxyIntegration: str = "0"
    haproxyAclRef: str = ""
    haproxyActionRef: str = ""
    haproxyServerRef: str = ""
    haproxyBackendRef: str = ""
    logLevel: str = "normal"
    showIntro: str = "1"
