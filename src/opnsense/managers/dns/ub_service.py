# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Unbound service controller — start/stop/restart/reconfigure.

API domain: /api/unbound/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  unbound/service/status
    start        POST unbound/service/start
    stop         POST unbound/service/stop
    restart      POST unbound/service/restart
    reconfigure  POST unbound/service/reconfigure

``status`` reports ``'disabled'`` while ``general.enabled='0'`` (see
:class:`~opnsense.managers.dns.ub_settings.UbSettingsManager`) — a start
request is pointless in that state; enable the resolver first.

Reference: https://docs.opnsense.org/manual/unbound.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class UbServiceManager(BaseServiceManager):
    """Control the OPNsense Unbound resolver service.

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = UbServiceManager(client)
            await mgr.ensure("reconfigured")     # re-read forwards/overrides
            await mgr.ensure("running")          # start if enabled but down

    Input (ensure):
        state: ``'running'`` | ``'stopped'`` | ``'reconfigured'``.

    Output (EnsureResult):
        changed: bool — True if state was modified.
        action:  ``'started'`` | ``'stopped'`` | ``'restarted'`` |
                 ``'reconfigured'`` | ``'noop'``.
        before:  ``{'status': '<previous>'}``.
        after:   ``{'status': '<current>'}``.
    """

    _endpoint = "unbound/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the Unbound service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
