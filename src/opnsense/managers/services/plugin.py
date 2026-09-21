# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""OPNsense plugin manager — list, install, remove firmware plugins.

NOT a BaseManager — plugins use the firmware API, not CRUD endpoints.

Endpoints:
    list        GET  core/firmware/info
    install     POST core/firmware/install/{package_name}
    remove      POST core/firmware/remove/{package_name}
    status      GET  core/firmware/upgradestatus
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseServerError, OpnsenseTimeoutError
from opnsense.models.base import EnsureResult

logger = logging.getLogger(__name__)


class PluginManager:
    """Manage OPNsense plugins — list, install, remove.

    NOT a BaseManager — plugins use firmware API, not CRUD endpoints.

    Usage::

        async with OpnsenseClient(...) as client:
            mgr = PluginManager(client)
            plugins = await mgr.list_plugins()
            await mgr.install("os-ddclient")
            await mgr.remove("os-ddclient")

    Input (install/remove):
        package_name:  Plugin package name (e.g. 'os-ddclient')

    Output (list_plugins):
        List of dicts with name, version, comment, installed status

    Output (install/remove):
        Dict with status and msg_uuid for tracking
    """

    def __init__(self, client: OpnsenseClient) -> None:
        """Initialise the plugin manager.

        Args:
            client: An :class:`OpnsenseClient` instance.
        """
        self._client = client

    async def list_plugins(self) -> list[dict[str, Any]]:
        """List all available plugins with install status.

        Returns:
            List of plugin dicts with name, version, comment, installed.
        """
        try:
            body = await self._client.get("core/firmware/info")
            packages: list[dict[str, Any]] = body.get("package", [])
            return [p for p in packages if p.get("name", "").startswith("os-")]
        except Exception as exc:
            logger.error(
                "list_plugins failed: %s",
                exc,
                extra={"action": "list_plugins_failed", "error": str(exc)},
            )
            raise

    async def list_installed(self) -> list[dict[str, Any]]:
        """List only installed plugins.

        Returns:
            List of installed plugin dicts.
        """
        try:
            plugins = await self.list_plugins()
            return [p for p in plugins if p.get("installed") == "1"]
        except Exception as exc:
            logger.error(
                "list_installed failed: %s",
                exc,
                extra={"action": "list_installed_failed", "error": str(exc)},
            )
            raise

    async def is_installed(self, package_name: str) -> bool:
        """Check if a specific plugin is installed.

        Args:
            package_name: Plugin package name (e.g. 'os-ddclient').

        Returns:
            True if the plugin is installed, False otherwise.
        """
        try:
            plugins = await self.list_plugins()
            return any(p.get("name") == package_name and p.get("installed") == "1" for p in plugins)
        except Exception as exc:
            logger.error(
                "is_installed failed for %s: %s",
                package_name,
                exc,
                extra={
                    "action": "is_installed_failed",
                    "package": package_name,
                    "error": str(exc),
                },
            )
            raise

    async def install(self, package_name: str) -> dict[str, Any]:
        """Install a plugin.

        Args:
            package_name: Plugin package name (e.g. 'os-ddclient').

        Returns:
            Dict with status and msg_uuid for tracking.
        """
        try:
            result: dict[str, Any] = await self._client.post(
                f"core/firmware/install/{package_name}", data={}
            )
            logger.info(
                "install requested %s",
                package_name,
                extra={"action": "install_requested", "package": package_name},
            )
            return result
        except Exception as exc:
            logger.error(
                "install failed for %s: %s",
                package_name,
                exc,
                extra={
                    "action": "install_failed",
                    "package": package_name,
                    "error": str(exc),
                },
            )
            raise

    async def remove(self, package_name: str) -> dict[str, Any]:
        """Remove a plugin.

        Args:
            package_name: Plugin package name (e.g. 'os-ddclient').

        Returns:
            Dict with status and msg_uuid for tracking.
        """
        try:
            result: dict[str, Any] = await self._client.post(
                f"core/firmware/remove/{package_name}", data={}
            )
            logger.info(
                "remove requested %s",
                package_name,
                extra={"action": "remove_requested", "package": package_name},
            )
            return result
        except Exception as exc:
            logger.error(
                "remove failed for %s: %s",
                package_name,
                exc,
                extra={
                    "action": "remove_failed",
                    "package": package_name,
                    "error": str(exc),
                },
            )
            raise

    async def get_status(self) -> dict[str, Any]:
        """Get firmware/upgrade status (check if install/remove is done).

        Returns:
            Dict with upgrade status information.
        """
        try:
            return await self._client.get("core/firmware/upgradestatus")
        except Exception as exc:
            logger.error(
                "get_status failed: %s",
                exc,
                extra={"action": "get_status_failed", "error": str(exc)},
            )
            raise

    # ------------------------------------------------------------------
    # Idempotent ensure — the firmware job API says "done" even when it REFUSED
    # ------------------------------------------------------------------

    # Verdict lines the backend writes to the job log instead of failing the job.
    _REFUSALS: tuple[tuple[str, str], ...] = (
        (
            "Installation out of date",
            "base image out of date — apply the pending point update first",
        ),
        ("No packages available to install", "unknown package name"),
        ("No packages available to remove", "unknown package name"),
    )

    async def ensure(
        self,
        package_name: str,
        state: str = "present",
        wait: bool = True,
        timeout: int = 300,
        interval: float = 5.0,
        check_mode: bool = False,
        verify_retries: int = 12,
        verify_interval: float = 5.0,
    ) -> EnsureResult:
        """Ensure a plugin is installed (``present``) or removed (``absent``).

        Reads the installed state first (noop when it already matches), fires the
        firmware job, waits for ``upgradestatus`` to report ``done`` and then reads
        the VERDICT from the job log — the backend reports ``done`` for a refused
        install too (e.g. a fresh 26.7.0 image: "Installation out of date. The update
        to opnsense-26.7.3_11 is required."). Finally re-reads the installed state.

        Args:
            package_name: Plugin package name (e.g. ``'os-chrony'``).
            state:        ``'present'`` | ``'absent'``.
            wait:         Poll the job until done (``False`` = fire and forget).
            timeout:      Seconds to wait for the job.
            interval:     Poll interval in seconds.
            check_mode:   Report without changing anything.
            verify_retries: Re-reads of the installed state after the job (the package cache lags;
                           the appliance may still be installing its own plugin list).
            verify_interval: Seconds between those re-reads.

        Returns:
            ``EnsureResult`` — ``action`` ``'installed'`` | ``'removed'`` | ``'noop'``,
            ``before``/``after`` = ``{'installed': bool}``.

        Raises:
            ValueError:            Unsupported ``state``.
            OpnsenseServerError:   The backend refused the job, or the package state
                                   did not change although the job reported done.
            OpnsenseTimeoutError:  The job did not finish within ``timeout``.
        """
        if state not in ("present", "absent"):
            raise ValueError(f"PluginManager.ensure: state must be present|absent, got {state!r}")
        want = state == "present"
        action = "installed" if want else "removed"
        installed = await self.is_installed(package_name)
        before = {"installed": installed}
        if installed == want:
            logger.debug(
                "noop plugin %s already %s",
                package_name,
                state,
                extra={"action": "noop", "package": package_name},
            )
            return EnsureResult(changed=False, action="noop", before=before, after=before)
        if check_mode:
            logger.info(
                "%s check_mode=True %s",
                action,
                package_name,
                extra={"action": action, "package": package_name, "check_mode": True},
            )
            return EnsureResult(
                changed=True, action=action, before=before, after={"installed": want}
            )
        # Never fire into a running firmware job (the appliance's own post-update plugin
        # reinstall, a check, another install): it ends in a job 'error'.
        await self.wait_for_idle(timeout=timeout, interval=interval)
        if want:
            await self.install(package_name)
        else:
            await self.remove(package_name)
        if not wait:
            return EnsureResult(
                changed=True, action=action, before=before, after={"installed": want}
            )
        log = await self._wait_for_job(timeout=timeout, interval=interval)
        self._verdict(package_name, log)
        # core/firmware/info serves a package cache that lags the job — and right after a
        # firmware update the appliance re-installs the plugins its config lists on its own, so
        # the job may answer "Nothing to do" while the cache still says absent (2026-09-21). Re-read
        # for a while before calling it a failure.
        after_installed = await self.is_installed(package_name)
        tries = 0
        while after_installed != want and tries < verify_retries:
            tries += 1
            await asyncio.sleep(verify_interval)
            after_installed = await self.is_installed(package_name)
        if after_installed != want:
            tail = " | ".join(line for line in log.splitlines()[-4:] if line.strip())
            logger.error(
                "plugin %s: job done but state unchanged",
                package_name,
                extra={"action": f"{action}_failed", "package": package_name, "log_tail": tail},
            )
            raise OpnsenseServerError(
                f"{package_name}: firmware job reported done but the package is still "
                f"{'absent' if want else 'installed'} — job log tail: {tail}"
            )
        logger.info(
            "%s %s", action, package_name, extra={"action": action, "package": package_name}
        )
        return EnsureResult(
            changed=True, action=action, before=before, after={"installed": after_installed}
        )

    async def wait_for_idle(self, timeout: int = 300, interval: float = 5.0) -> None:
        """Poll ``core/firmware/running`` until the firmware subsystem reports ``ready``."""
        waited = 0.0
        while True:
            body = await self._client.get("core/firmware/running")
            if str(body.get("status", "")) == "ready":
                return
            if waited >= timeout:
                raise OpnsenseTimeoutError(f"firmware subsystem still busy after {timeout}s")
            await asyncio.sleep(interval)
            waited += interval

    async def _wait_for_job(self, timeout: int, interval: float) -> str:
        """Poll ``core/firmware/upgradestatus`` until ``status == 'done'``; return its log.

        The appliance derives the status from its progress log: ``done`` once it holds
        ``***DONE***``, ``running`` while it fills, and ``error`` when it is EMPTY — which is
        what a job that has just been fired looks like before its first line lands
        (``FirmwareController::upgradestatusAction``, verified on 26.7.4). ``error`` is
        therefore "not started yet", never a failure: keep polling until ``done`` or the
        timeout. Failures surface in the finished log (``_check_job_log``) or as a timeout.
        """
        waited = 0.0
        while True:
            status = await self.get_status()
            if str(status.get("status", "")) == "done":
                return str(status.get("log", "") or "")
            if waited >= timeout:
                logger.error(
                    "firmware job timeout after %ss",
                    timeout,
                    extra={"action": "job_timeout", "timeout": timeout},
                )
                raise OpnsenseTimeoutError(
                    f"firmware job still {status.get('status')!r} after {timeout}s"
                )
            await asyncio.sleep(interval)
            waited += interval

    def _verdict(self, package_name: str, log: str) -> None:
        """Raise when the job log carries a refusal the backend did not report as a failure."""
        for marker, meaning in self._REFUSALS:
            if marker in log:
                line = next((ln.strip() for ln in log.splitlines() if marker in ln), marker)
                logger.error(
                    "plugin %s refused: %s",
                    package_name,
                    line,
                    extra={"action": "refused", "package": package_name, "reason": meaning},
                )
                raise OpnsenseServerError(
                    f"{package_name}: firmware backend refused the job ({meaning}): {line}"
                )
