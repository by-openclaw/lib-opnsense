# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dynamic DNS (os-ddclient) service controller — start/stop/restart/reconfigure.

API domain: /api/dyndns/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  dyndns/service/status
    start        POST dyndns/service/start
    stop         POST dyndns/service/stop
    restart      POST dyndns/service/restart
    reconfigure  POST dyndns/service/reconfigure

Accounts are managed by :class:`~opnsense.managers.services.ddns_account.DdnsAccountManager`;
a ``restart`` after an account change makes ddclient publish the active WAN address now.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class DdnsServiceManager(BaseServiceManager):
    """Control the OPNsense Dynamic DNS service (os-ddclient).

    Inherits ``status``/``start``/``stop``/``restart``/``reconfigure`` and the
    idempotent ``ensure(state=...)`` semantics from :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            await DdnsServiceManager(client).ensure("reconfigured")
    """

    _endpoint = "dyndns/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the DDNS service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
