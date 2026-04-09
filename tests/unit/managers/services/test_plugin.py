# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.plugin.PluginManager.

NOT a BaseManager — custom firmware API methods: list, install, remove.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.plugin import PluginManager


@pytest.fixture
def plugin_client() -> AsyncMock:
    """Create a mocked OpnsenseClient for plugin tests."""
    client = AsyncMock(spec=OpnsenseClient)
    client._base_url = "https://opnsense.example.com"
    return client


SAMPLE_PACKAGES = [
    {"name": "os-ddclient", "version": "1.0", "comment": "Dynamic DNS", "installed": "1"},
    {"name": "os-haproxy", "version": "4.5", "comment": "HAProxy", "installed": "0"},
    {"name": "os-theme-cicada", "version": "1.0", "comment": "Cicada theme", "installed": "0"},
    {"name": "pkg", "version": "1.21", "comment": "Package manager", "installed": "1"},
]


@pytest.mark.asyncio
class TestListPlugins:
    """Tests for list_plugins()."""

    async def test_list_plugins_returns_os_packages(self, plugin_client: AsyncMock) -> None:
        """list_plugins filters to os-* packages only."""
        plugin_client.get.return_value = {"package": SAMPLE_PACKAGES}

        mgr = PluginManager(plugin_client)
        result = await mgr.list_plugins()

        assert len(result) == 3
        names = [p["name"] for p in result]
        assert "os-ddclient" in names
        assert "os-haproxy" in names
        assert "os-theme-cicada" in names
        assert "pkg" not in names
        plugin_client.get.assert_awaited_once_with("core/firmware/info")

    async def test_list_plugins_empty_when_no_packages(self, plugin_client: AsyncMock) -> None:
        """list_plugins returns empty list when no package key."""
        plugin_client.get.return_value = {}

        mgr = PluginManager(plugin_client)
        result = await mgr.list_plugins()

        assert result == []

    async def test_list_plugins_error_reraises(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.side_effect = RuntimeError("connection refused")

        mgr = PluginManager(plugin_client)
        with pytest.raises(RuntimeError, match="connection refused"):
            await mgr.list_plugins()


@pytest.mark.asyncio
class TestListInstalled:
    """Tests for list_installed()."""

    async def test_list_installed_returns_only_installed(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.return_value = {"package": SAMPLE_PACKAGES}

        mgr = PluginManager(plugin_client)
        result = await mgr.list_installed()

        assert len(result) == 1
        assert result[0]["name"] == "os-ddclient"


@pytest.mark.asyncio
class TestIsInstalled:
    """Tests for is_installed()."""

    async def test_is_installed_true(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.return_value = {"package": SAMPLE_PACKAGES}

        mgr = PluginManager(plugin_client)
        assert await mgr.is_installed("os-ddclient") is True

    async def test_is_installed_false(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.return_value = {"package": SAMPLE_PACKAGES}

        mgr = PluginManager(plugin_client)
        assert await mgr.is_installed("os-haproxy") is False

    async def test_is_installed_false_for_missing(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.return_value = {"package": SAMPLE_PACKAGES}

        mgr = PluginManager(plugin_client)
        assert await mgr.is_installed("os-nonexistent") is False


@pytest.mark.asyncio
class TestInstall:
    """Tests for install()."""

    async def test_install_posts_to_firmware_endpoint(self, plugin_client: AsyncMock) -> None:
        plugin_client.post.return_value = {"status": "ok", "msg_uuid": "abc-123"}

        mgr = PluginManager(plugin_client)
        result = await mgr.install("os-ddclient")

        assert result["status"] == "ok"
        plugin_client.post.assert_awaited_once_with("core/firmware/install/os-ddclient", data={})

    async def test_install_error_reraises(self, plugin_client: AsyncMock) -> None:
        plugin_client.post.side_effect = RuntimeError("install failed")

        mgr = PluginManager(plugin_client)
        with pytest.raises(RuntimeError, match="install failed"):
            await mgr.install("os-ddclient")


@pytest.mark.asyncio
class TestRemove:
    """Tests for remove()."""

    async def test_remove_posts_to_firmware_endpoint(self, plugin_client: AsyncMock) -> None:
        plugin_client.post.return_value = {"status": "ok", "msg_uuid": "def-456"}

        mgr = PluginManager(plugin_client)
        result = await mgr.remove("os-ddclient")

        assert result["status"] == "ok"
        plugin_client.post.assert_awaited_once_with("core/firmware/remove/os-ddclient", data={})

    async def test_remove_error_reraises(self, plugin_client: AsyncMock) -> None:
        plugin_client.post.side_effect = RuntimeError("remove failed")

        mgr = PluginManager(plugin_client)
        with pytest.raises(RuntimeError, match="remove failed"):
            await mgr.remove("os-ddclient")


@pytest.mark.asyncio
class TestGetStatus:
    """Tests for get_status()."""

    async def test_get_status_returns_dict(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.return_value = {"status": "done", "log": "complete"}

        mgr = PluginManager(plugin_client)
        result = await mgr.get_status()

        assert result["status"] == "done"
        plugin_client.get.assert_awaited_once_with("core/firmware/upgradestatus")

    async def test_get_status_error_reraises(self, plugin_client: AsyncMock) -> None:
        plugin_client.get.side_effect = RuntimeError("timeout")

        mgr = PluginManager(plugin_client)
        with pytest.raises(RuntimeError, match="timeout"):
            await mgr.get_status()
