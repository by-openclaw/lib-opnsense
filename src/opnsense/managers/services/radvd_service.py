# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense radvd service controller — start/stop/restart/reconfigure.

API domain: /api/radvd/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  radvd/service/status
    start        POST radvd/service/start
    stop         POST radvd/service/stop
    restart      POST radvd/service/restart
    reconfigure  POST radvd/service/reconfigure

Reference: https://docs.opnsense.org/manual/router_advertisements.html
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class RadvdServiceManager(BaseServiceManager):
    """Control the OPNsense radvd (Router Advertisement Daemon) service.

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = RadvdServiceManager(client)
            await mgr.ensure("running")        # start if not already up
            await mgr.ensure("reconfigured")    # re-read radvd.conf

    Input (ensure):
        state: ``'running'`` | ``'stopped'`` | ``'reconfigured'``.

    Output (EnsureResult):
        changed: bool — True if state was modified.
        action:  ``'started'`` | ``'stopped'`` | ``'restarted'`` |
                 ``'reconfigured'`` | ``'noop'``.
        before:  ``{'status': '<previous>'}``.
        after:   ``{'status': '<current>'}``.
    """

    _endpoint = "radvd/service"
    _apply_timeout = 30

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the radvd service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
