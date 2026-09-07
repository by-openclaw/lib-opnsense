# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""QEMU guest agent service controller (os-qemu-guest-agent) — start/stop/reconfigure.

API domain: /api/qemuguestagent/service
Pattern:    BaseServiceManager — idempotent state transitions.

Endpoints:
    status       GET  qemuguestagent/service/status
    start        POST qemuguestagent/service/start
    stop         POST qemuguestagent/service/stop
    restart      POST qemuguestagent/service/restart
    reconfigure  POST qemuguestagent/service/reconfigure

``status`` reports ``'disabled'`` while the plugin is switched off in its settings — a start
request is pointless in that state; enable it through the settings manager first.
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class QemuGuestAgentServiceManager(BaseServiceManager):
    """Control the OPNsense QEMU guest agent service (os-qemu-guest-agent).

    Inherits the full ``status``/``start``/``stop``/``restart``/``reconfigure``
    contract and the idempotent ``ensure(state=...)`` semantics from
    :class:`BaseServiceManager`.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = QemuGuestAgentServiceManager(client)
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

    _endpoint = "qemuguestagent/service"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)
