# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense Monit daemon controller (os-monit) — start/stop/restart/reconfigure.

API domain: /api/monit/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  monit/service/status
    start        POST monit/service/start
    stop         POST monit/service/stop
    restart      POST monit/service/restart
    reconfigure  POST monit/service/reconfigure

Not to be confused with :class:`~opnsense.managers.monit.service.MonitServiceManager`, which
manages the *monitored service entries* (``monit/settings/*Service``). This class drives the
daemon itself.

Gotcha (OPNsense 26.7, os-monit): ``reconfigure`` regenerates ``monitrc``, runs the syntax
test and only then (re)starts the daemon. A refused config answers HTTP 200 with
``{"status": "failed", "message": ...}`` — the client raises ``OpnsenseServerError`` for it,
so ``ensure("reconfigured")`` / ``ensure("running")`` fail loudly instead of leaving Monit down.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class MonitDaemonManager(BaseServiceManager):
    """Control the OPNsense Monit daemon (os-monit).

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = MonitDaemonManager(client)
            await mgr.ensure("reconfigured")   # regenerate monitrc, syntax test, (re)start
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

    _endpoint = "monit/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the daemon manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
