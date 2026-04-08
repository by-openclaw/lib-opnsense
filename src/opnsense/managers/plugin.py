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

import logging
from typing import Any

from opnsense.client import OpnsenseClient

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
