# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense firmware manager — check / status / update / upgrade / wait-for-version.

API domain: /api/core/firmware
Pattern:    NOT a BaseManager — the firmware endpoints are async jobs, not CRUD.

Endpoints:
    check          POST core/firmware/check          (async job → poll upgradestatus)
    status         GET  core/firmware/status         (resolved: none|update|upgrade + version)
    update         POST core/firmware/update         (point release; REBOOTS the device)
    upgrade        POST core/firmware/upgrade        (major version; REBOOTS the device)
    upgradestatus  POST core/firmware/upgradestatus  (job progress + log)

Applying updates is a deliberate per-environment window, never part of a converge:
``ensure()`` only acts when the caller asks for it and the device reports a pending
update/upgrade. ``wait_for_version`` tolerates the connection errors of the reboot.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.exceptions import (
    OpnsenseConnectionError,
    OpnsenseServerError,
    OpnsenseTimeoutError,
)
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class FirmwareManager:
    """Drive the OPNsense firmware job API.

    Usage::

        async with OpnsenseClient(...) as client:
            fw = FirmwareManager(client)
            status = await fw.check()                # runs the check job, returns resolved status
            if status["status"] == "update":
                await fw.ensure("updated", target="26.7.3")  # update, wait for the reboot INTO it

    Input (ensure):
        state:  ``'updated'`` (apply a pending point update) | ``'upgraded'`` (apply a
                pending major upgrade — or the pending update if that is what is queued).
        target: version substring to wait for after the reboot (``None`` = do not wait).

    Output (EnsureResult):
        changed: True if an update/upgrade was fired.
        action:  ``'updated'`` | ``'upgraded'`` | ``'noop'``.
        before:  ``{'product_version', 'status'}`` as resolved by the check.
        after:   same shape after the wait (or the projection in ``check_mode``).
    """

    _endpoint = "core/firmware"

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the firmware manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    async def status(self) -> dict[str, Any]:
        """Return the resolved firmware status (``status``, ``product_version``, packages…)."""
        try:
            return await self._client.get(f"{self._endpoint}/status")
        except Exception as exc:
            logger.error(
                "firmware status failed: %s",
                exc,
                extra={"action": "status_failed", "error": str(exc)},
            )
            raise

    async def job_status(self) -> dict[str, Any]:
        """Return the running/last job progress (``status``: running|done, ``log``)."""
        return await self._client.post(f"{self._endpoint}/upgradestatus", data={})

    async def check(self, timeout: int = 120, interval: float = 5.0) -> dict[str, Any]:
        """Run the update check job, wait for it, then return the resolved status.

        Reading ``status`` without a fresh check returns stale (often ``'none'``) data.
        """
        try:
            await self._client.post(f"{self._endpoint}/check", data={})
            await self._wait_job(timeout=timeout, interval=interval)
            resolved = await self.status()
        except Exception as exc:
            logger.error(
                "firmware check failed: %s",
                exc,
                extra={"action": "check_failed", "error": str(exc)},
            )
            raise
        logger.info(
            "firmware check: %s (%s)",
            resolved.get("status"),
            resolved.get("product_version"),
            extra={
                "action": "checked",
                "status": resolved.get("status"),
                "product_version": resolved.get("product_version"),
            },
        )
        return resolved

    async def update(self) -> dict[str, Any]:
        """Apply the pending point update (the device reboots). Not idempotent — use ``ensure``."""
        return await self._fire("update")

    async def upgrade(self) -> dict[str, Any]:
        """Apply the pending major upgrade (the device reboots). Not idempotent — use ``ensure``."""
        return await self._fire("upgrade")

    async def wait_for_version(
        self, target: str, timeout: int = 1500, interval: float = 30.0
    ) -> str:
        """Poll ``info`` until ``product_version`` contains ``target`` (reboot-tolerant).

        Connection/timeout/server errors while the device reboots are expected and
        swallowed; anything else propagates.

        Returns:
            The ``product_version`` string that matched.

        Raises:
            OpnsenseTimeoutError: ``target`` never appeared within ``timeout`` seconds.
        """
        waited = 0.0
        last = ""
        while True:
            try:
                # One attempt per poll: the loop below is the retry. max_retries counts attempts
                # in the client, so 0 would never send the request ("failed after 0 attempts").
                # ``info`` carries product_version on every boot; ``status`` reports none until a
                # check job has run (a freshly rebooted appliance never reached the target).
                body = await self._client.get(f"{self._endpoint}/info", timeout=20, max_retries=1)
                last = str(body.get("product_version", "") or "")
                if target in last:
                    logger.info(
                        "device is on %s",
                        last,
                        extra={"action": "version_reached", "product_version": last},
                    )
                    return last
            except (OpnsenseConnectionError, OpnsenseTimeoutError, OpnsenseServerError) as exc:
                logger.debug(
                    "waiting for %s: %s",
                    target,
                    exc,
                    extra={"action": "version_wait", "error": str(exc)},
                )
            if waited >= timeout:
                logger.error(
                    "timeout waiting for version %s (last seen %r)",
                    target,
                    last,
                    extra={"action": "version_timeout", "target": target, "last": last},
                )
                raise OpnsenseTimeoutError(
                    f"device did not report version {target!r} within {timeout}s (last: {last!r})"
                )
            await asyncio.sleep(interval)
            waited += interval

    async def ensure(
        self,
        state: str = "updated",
        target: str | None = None,
        check_mode: bool = False,
        check_timeout: int = 120,
        wait_timeout: int = 1500,
        wait_interval: float = 30.0,
    ) -> EnsureResult:
        """Apply a pending update/upgrade only when the device reports one.

        Args:
            state:        ``'updated'`` | ``'upgraded'``.
            target:       version substring to wait for after the reboot (``None`` = no wait).
            check_mode:   report without firing anything.
            check_timeout: seconds allowed for the check job.
            wait_timeout:  seconds allowed for the reboot into ``target``.
            wait_interval: poll interval while waiting for ``target``.
        """
        if state not in ("updated", "upgraded"):
            raise ValueError(
                f"FirmwareManager.ensure: state must be updated|upgraded, got {state!r}"
            )
        resolved = await self.check(timeout=check_timeout)
        pending = str(resolved.get("status", "") or "")
        before = {"product_version": resolved.get("product_version"), "status": pending}
        if state == "updated":
            verb = "update" if pending == "update" else None
        else:
            verb = (
                "upgrade" if pending == "upgrade" else ("update" if pending == "update" else None)
            )
        if verb is None:
            logger.debug(
                "noop firmware: nothing pending (%s)",
                pending,
                extra={"action": "noop", "status": pending},
            )
            return EnsureResult(changed=False, action="noop", before=before, after=before)
        if check_mode:
            logger.info(
                "%s check_mode=True (pending %s)",
                state,
                pending,
                extra={"action": state, "check_mode": True},
            )
            return EnsureResult(
                changed=True,
                action=state,
                before=before,
                after={"product_version": target or before["product_version"], "status": "pending"},
            )
        await self._fire(verb)
        after: dict[str, Any] = {"product_version": before["product_version"], "status": "applying"}
        if target:
            after = {
                "product_version": await self.wait_for_version(
                    target, timeout=wait_timeout, interval=wait_interval
                ),
                "status": "none",
            }
        return EnsureResult(changed=True, action=state, before=before, after=after)

    async def _fire(self, verb: str) -> dict[str, Any]:
        try:
            result = await self._client.post(f"{self._endpoint}/{verb}", data={})
        except OpnsenseConnectionError as exc:
            if verb in ("update", "upgrade"):
                # The appliance restarts its web server as soon as it starts applying; the
                # response can be cut mid-stream. The request went out — the version wait that
                # follows is the proof, not this reply.
                logger.warning(
                    "firmware %s: connection dropped while the device started applying (%s)",
                    verb,
                    exc,
                    extra={"action": f"{verb}_requested", "error": str(exc)},
                )
                return {}
            raise
        except Exception as exc:
            logger.error(
                "firmware %s failed: %s",
                verb,
                exc,
                extra={"action": f"{verb}_failed", "error": str(exc)},
            )
            raise
        logger.warning(
            "firmware %s requested — the device will reboot",
            verb,
            extra={"action": f"{verb}_requested"},
        )
        return result

    async def _wait_job(self, timeout: int, interval: float) -> str:
        waited = 0.0
        while True:
            job = await self.job_status()
            if str(job.get("status", "")) == "done":
                return str(job.get("log", "") or "")
            if waited >= timeout:
                raise OpnsenseTimeoutError(
                    f"firmware job still {job.get('status')!r} after {timeout}s"
                )
            await asyncio.sleep(interval)
            waited += interval
