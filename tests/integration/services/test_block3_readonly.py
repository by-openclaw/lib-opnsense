# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — firmware / plugin / core-service / ddns / netflow managers, READ-ONLY.

Safety boundaries:
    - PluginManager.ensure only asserts a noop on an already-installed plugin and a
      check_mode preview of its removal — nothing is installed or removed.
    - FirmwareManager: status read + check job (no update/upgrade is ever fired).
    - CoreServiceManager: ntpd is expected stopped (chrony owns :123) → noop; unknown → noop.
    - Ddns/Netflow: status + reconfigure only.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.core_service import CoreServiceManager
from opnsense.managers.services.ddns_service import DdnsServiceManager
from opnsense.managers.services.firmware import FirmwareManager
from opnsense.managers.services.netflow_service import NetflowServiceManager
from opnsense.managers.services.plugin import PluginManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestPluginEnsure:
    async def test_01_installed_plugin_is_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        installed = [p["name"] for p in await mgr.list_installed()]
        if not installed:
            pytest.skip("no plugin installed on this device")
        r = await mgr.ensure(installed[0], "present")
        assert r.action == "noop" and r.before == {"installed": True}

    async def test_02_check_mode_removal_does_not_fire(self, opn_client: OpnsenseClient) -> None:
        mgr = PluginManager(opn_client)
        installed = [p["name"] for p in await mgr.list_installed()]
        if not installed:
            pytest.skip("no plugin installed on this device")
        r = await mgr.ensure(installed[0], "absent", check_mode=True)
        assert r.changed is True and r.action == "removed"
        assert await mgr.is_installed(installed[0]) is True


class TestFirmwareReadOnly:
    async def test_01_status_has_version(self, opn_client: OpnsenseClient) -> None:
        st = await FirmwareManager(opn_client).status()
        assert st.get("product_version"), st

    async def test_02_check_resolves_status(self, opn_client: OpnsenseClient) -> None:
        st = await FirmwareManager(opn_client).check()
        assert st.get("status") in {"none", "update", "upgrade", "error"}, st

    async def test_03_ensure_check_mode_never_fires(self, opn_client: OpnsenseClient) -> None:
        r = await FirmwareManager(opn_client).ensure("updated", check_mode=True)
        assert r.action in {"noop", "updated"}


class TestCoreService:
    async def test_01_unknown_daemon_stopped_is_noop(self, opn_client: OpnsenseClient) -> None:
        r = await CoreServiceManager(opn_client).ensure("inttest-nope", "stopped")
        assert r.action == "noop" and r.before == {"status": "unknown"}

    async def test_02_registry_lists_known_daemons(self, opn_client: OpnsenseClient) -> None:
        ids = {row.get("id") for row in await CoreServiceManager(opn_client).list()}
        assert "openssh" in ids or "syslog-ng" in ids, ids


class TestDdnsAndNetflow:
    async def test_01_ddns_status_known(self, opn_client: OpnsenseClient) -> None:
        assert await DdnsServiceManager(opn_client).status() in {
            "running",
            "stopped",
            "disabled",
            "unknown",
        }

    async def test_02_netflow_status_and_reconfigure(self, opn_client: OpnsenseClient) -> None:
        mgr = NetflowServiceManager(opn_client)
        assert await mgr.status() in {"running", "stopped"}
        assert (await mgr.ensure("reconfigured")).action == "reconfigured"
