# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense core service controller — start/stop/restart any registered daemon by name.

API domain: /api/core/service
Pattern:    NOT a BaseServiceManager (that one binds a single ``<plugin>/service``
            controller); this drives the generic registry used by legacy daemons that
            have no MVC controller of their own (``ntpd``, ``syslog-ng``, ``openssh``, …).

Endpoints:
    search   GET  core/service/search              ({rows: [{id, name, running, locked}]})
    start    POST core/service/start/<name>
    stop     POST core/service/stop/<name>
    restart  POST core/service/restart/<name>
"""

from __future__ import annotations

import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class CoreServiceManager:
    """Ensure a registered daemon is running / stopped / restarted.

    Usage::

        async with OpnsenseClient(...) as client:
            svc = CoreServiceManager(client)
            await svc.ensure("ntpd", "stopped")      # chrony owns :123 now
            await svc.ensure("syslog-ng", "restarted")

    Output (EnsureResult):
        changed: True if an action was fired.
        action:  ``'started'`` | ``'stopped'`` | ``'restarted'`` | ``'noop'``.
        before/after: ``{'status': 'running'|'stopped'|'unknown'}``.
    """

    _endpoint = "core/service"

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the core service manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    async def list(self) -> list[dict[str, Any]]:
        """Return the service registry rows (``id``, ``name``, ``running``, ``locked``)."""
        body = await self._client.get(f"{self._endpoint}/search")
        rows = body.get("rows", []) if isinstance(body, dict) else []
        return [r for r in rows if isinstance(r, dict)]

    async def status(self, name: str) -> str:
        """``'running'`` | ``'stopped'`` for a registered daemon; ``'unknown'`` if unregistered."""
        for row in await self.list():
            if row.get("id") == name or row.get("name") == name:
                return (
                    "running"
                    if str(row.get("running", "0")) in ("1", "True", "true")
                    else "stopped"
                )
        return "unknown"

    async def ensure(
        self, name: str, state: str = "running", check_mode: bool = False
    ) -> EnsureResult:
        """Ensure ``name`` is in ``state`` (``running`` | ``stopped`` | ``restarted``).

        ``restarted`` always fires (never idempotent). An ``unknown`` daemon counts as
        stopped, so ``stopped`` is a noop and ``running`` attempts a start.
        """
        if state not in ("running", "stopped", "restarted"):
            raise ValueError(
                f"CoreServiceManager.ensure: state must be running|stopped|restarted, got {state!r}"
            )
        before = await self.status(name)
        before_dict = {"status": before}
        verb, action = {
            "running": ("start", "started"),
            "stopped": ("stop", "stopped"),
            "restarted": ("restart", "restarted"),
        }[state]
        if (state == "running" and before == "running") or (
            state == "stopped" and before in ("stopped", "unknown")
        ):
            logger.debug(
                "noop %s already %s", name, before, extra={"action": "noop", "service": name}
            )
            return EnsureResult(changed=False, action="noop", before=before_dict, after=before_dict)
        if check_mode:
            return EnsureResult(
                changed=True,
                action=action,
                before=before_dict,
                after={"status": "running" if state != "stopped" else "stopped"},
            )
        try:
            await self._client.post(f"{self._endpoint}/{verb}/{name}", data={})
        except Exception as exc:
            logger.error(
                "%s %s failed: %s",
                verb,
                name,
                exc,
                extra={"action": f"{verb}_failed", "service": name, "error": str(exc)},
            )
            raise
        after = await self.status(name)
        logger.info(
            "%s %s",
            action,
            name,
            extra={"action": action, "service": name, "before": before, "after": after},
        )
        return EnsureResult(
            changed=True, action=action, before=before_dict, after={"status": after}
        )
