# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Kea DHCP service controller — start/stop/restart/reconfigure.

API domain: /api/kea/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  kea/service/status
    start        POST kea/service/start
    stop         POST kea/service/stop
    restart      POST kea/service/restart
    reconfigure  POST kea/service/reconfigure

``status`` reports ``'disabled'`` while both dhcpv4 and dhcpv6 ``general.enabled`` are ``0``.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class KeaServiceManager(BaseServiceManager):
    """Control the Kea DHCP daemons (v4 + v6 share one service controller).

    Usage::

        async with OpnsenseClient(...) as client:
            await KeaServiceManager(client).ensure("running")
    """

    _endpoint = "kea/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Kea service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
