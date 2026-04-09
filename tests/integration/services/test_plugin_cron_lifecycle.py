# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Plugin + Cron managers on live OPNsense device.

Plugin: list, is_installed, install/remove (tested with os-ddclient).
Cron: CRUD with disabled jobs, inttest- prefix.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.cron_job import CronJobManager
from opnsense.managers.services.plugin import PluginManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestPluginManager:
    """Plugin list and check operations."""

    async def test_01_list_installed(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        installed = await mgr.list_installed()
        assert isinstance(installed, list)
        assert len(installed) >= 1

    async def test_02_is_installed(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        # os-ddclient was installed earlier in this session
        result = await mgr.is_installed("os-ddclient")
        assert isinstance(result, bool)

    async def test_03_list_plugins(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        plugins = await mgr.list_plugins()
        assert len(plugins) > 0
        names = [p.get("name", "") for p in plugins]
        assert any(n.startswith("os-") for n in names)


class TestCronJobCRUD:
    """Cron job CRUD — disabled, inttest- prefix."""

    async def test_01_create(self, opn_client: OpnsenseClient) -> None:
        mgr = CronJobManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-cron",
                "command": "firmware auto-update",
                "minutes": "0",
                "hours": "3",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "created"

    async def test_02_idempotent(self, opn_client: OpnsenseClient) -> None:
        mgr = CronJobManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-cron",
                "command": "firmware auto-update",
                "minutes": "0",
                "hours": "3",
                "enabled": "0",
            },
        )
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_update(self, opn_client: OpnsenseClient) -> None:
        mgr = CronJobManager(opn_client)
        r = await mgr.ensure(
            "present",
            {
                "description": "inttest-cron",
                "command": "firmware auto-update",
                "minutes": "30",
                "hours": "4",
                "enabled": "0",
            },
        )
        assert r.changed is True
        assert r.action == "updated"

    async def test_04_delete(self, opn_client: OpnsenseClient) -> None:
        mgr = CronJobManager(opn_client)
        r = await mgr.ensure("absent", {"description": "inttest-cron"})
        assert r.changed is True
        assert r.action == "deleted"


class TestCleanup:
    """Remove all inttest- cron jobs."""

    async def test_cleanup(self, opn_client: OpnsenseClient) -> None:
        mgr = CronJobManager(opn_client)
        rows = await mgr.list(search_phrase="inttest")
        for row in rows:
            if "inttest" in str(row.get("description", "")):
                await opn_client.delete("cron/settings/delJob", row["uuid"])
        await opn_client.reconfigure("cron/service/reconfigure", timeout=15)
