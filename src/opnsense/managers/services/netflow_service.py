# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense NetFlow / Insight reporting controller — status + reconfigure.

API domain: /api/diagnostics/netflow
Pattern:    BaseServiceManager subset — the controller exposes ``status`` and
            ``reconfigure`` only (no start/stop/restart; the exporter follows the
            ``collect.enable`` setting in the netflow config the SEED owns).

Endpoints:
    status       GET  diagnostics/netflow/status       ({status: active|inactive, collectors})
    reconfigure  POST diagnostics/netflow/reconfigure  (restart flowd / flowd_aggregate)
"""

from __future__ import annotations

from opnsense.client import OpnsenseClient
from opnsense.core.base_service import BaseServiceManager


class NetflowServiceManager(BaseServiceManager):
    """Reconfigure the NetFlow exporter and read whether it is active.

    ``status`` maps the controller's ``active``/``inactive`` onto the
    ``running``/``stopped`` vocabulary of :class:`BaseServiceManager`. Only
    ``ensure('reconfigured')`` is meaningful — ``running``/``stopped`` would call
    start/stop endpoints this controller does not have.

    Usage::

        async with OpnsenseClient(...) as client:
            await NetflowServiceManager(client).ensure("reconfigured")
    """

    _endpoint = "diagnostics/netflow"
    _apply_timeout = 60

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the NetFlow controller.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        super().__init__(client)

    async def status(self) -> str:
        """``'running'`` when the exporter reports ``active``, ``'stopped'`` otherwise."""
        raw = await super().status()
        return "running" if raw == "active" else "stopped"
