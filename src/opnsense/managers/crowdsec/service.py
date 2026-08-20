# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense CrowdSec service controller — start/stop/restart/reconfigure.

API domain: /api/crowdsec/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  crowdsec/service/status
    start        POST crowdsec/service/start
    stop         POST crowdsec/service/stop
    restart      POST crowdsec/service/restart
    reconfigure  POST crowdsec/service/reconfigure

``ServiceController`` extends ``ApiMutableServiceControllerBase``, so the
start/stop/restart trio is inherited; ``reconfigure`` is declared by the plugin.

Note: ``service/status`` is authoritative. Reading the daemon state over SSH as
a non-root user returns "not running" because the pidfile is unreadable, which
is a false negative.

Reference: https://docs.opnsense.org/manual/how-tos/crowdsec.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class CrowdSecServiceManager(BaseServiceManager):
    """Control the OPNsense CrowdSec service.

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and idempotent ``ensure(state=...)`` from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = CrowdSecServiceManager(client)
            await mgr.ensure("running")
            await mgr.ensure("reconfigured")   # re-read config after a settings set

    Input (ensure):
        state: ``'running'`` | ``'stopped'`` | ``'reconfigured'``.

    Output (EnsureResult):
        changed: bool — True if state was modified.
        action:  ``'started'`` | ``'stopped'`` | ``'restarted'`` |
                 ``'reconfigured'`` | ``'noop'``.
        before:  ``{'status': '<previous>'}``.
        after:   ``{'status': '<current>'}``.
    """

    _endpoint = "crowdsec/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the CrowdSec service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
