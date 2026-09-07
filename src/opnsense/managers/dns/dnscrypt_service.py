# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense dnscrypt-proxy service controller (os-dnscrypt-proxy) — start/stop/restart/reconfigure.

API domain: /api/dnscryptproxy/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  dnscryptproxy/service/status
    start        POST dnscryptproxy/service/start
    stop         POST dnscryptproxy/service/stop
    restart      POST dnscryptproxy/service/restart
    reconfigure  POST dnscryptproxy/service/reconfigure

``status`` reports ``'disabled'`` while the plugin is switched off in its settings — a start
request is pointless in that state; enable it through the settings manager first.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class DnscryptProxyServiceManager(BaseServiceManager):
    """Control the OPNsense dnscrypt-proxy service (os-dnscrypt-proxy).

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = DnscryptProxyServiceManager(client)
            await mgr.ensure("reconfigured")   # apply changed settings
            await mgr.ensure("running")        # start if enabled but down

    Input (ensure):
        state: ``'running'`` | ``'stopped'`` | ``'reconfigured'``.

    Output (EnsureResult):
        changed: bool — True if state was modified.
        action:  ``'started'`` | ``'stopped'`` | ``'restarted'`` |
                 ``'reconfigured'`` | ``'noop'``.
        before:  ``{'status': '<previous>'}``.
        after:   ``{'status': '<current>'}``.
    """

    _endpoint = "dnscryptproxy/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
