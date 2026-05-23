# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Dnsmasq service controller — start/stop/restart/reconfigure.

API domain: /api/dnsmasq/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  dnsmasq/service/status
    start        POST dnsmasq/service/start
    stop         POST dnsmasq/service/stop
    restart      POST dnsmasq/service/restart
    reconfigure  POST dnsmasq/service/reconfigure

Reference: https://docs.opnsense.org/manual/dnsmasq.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class DnsmasqServiceManager(BaseServiceManager):
    """Control the OPNsense Dnsmasq DNS/DHCP/RA service.

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnsmasqServiceManager(client)
            await mgr.ensure("stopped")          # disable for Kea coexistence
            await mgr.ensure("reconfigured")     # reload dnsmasq.conf

    Input (ensure):
        state: ``'running'`` | ``'stopped'`` | ``'reconfigured'``.

    Output (EnsureResult):
        changed: bool — True if state was modified.
        action:  ``'started'`` | ``'stopped'`` | ``'restarted'`` |
                 ``'reconfigured'`` | ``'noop'``.
        before:  ``{'status': '<previous>'}``.
        after:   ``{'status': '<current>'}``.
    """

    _endpoint = "dnsmasq/service"
    _apply_timeout = 30

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Dnsmasq service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
