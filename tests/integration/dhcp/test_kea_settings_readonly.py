# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Kea general settings + service, READ-ONLY (noop / check_mode only)."""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.dhcp.kea4_settings import Kea4SettingsManager
from opnsense.managers.dhcp.kea6_settings import Kea6SettingsManager
from opnsense.managers.dhcp.kea_service import KeaServiceManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("cls", [Kea4SettingsManager, Kea6SettingsManager], ids=["kea4", "kea6"])
class TestKeaSettingsReadOnly:
    async def test_01_get_has_enabled(self, opn_client: OpnsenseClient, cls) -> None:
        assert (await cls(opn_client).get()).get("enabled") in ("0", "1")

    async def test_02_ensure_current_is_noop(self, opn_client: OpnsenseClient, cls) -> None:
        mgr = cls(opn_client)
        cur = await mgr.get()
        r = await mgr.ensure(
            "present", {"enabled": cur["enabled"], "valid_lifetime": cur["valid_lifetime"]}
        )
        assert r.action == "noop"

    async def test_03_check_mode(self, opn_client: OpnsenseClient, cls) -> None:
        mgr = cls(opn_client)
        before = await mgr.get()
        r = await mgr.ensure(
            "present", {"enabled": "0" if before["enabled"] == "1" else "1"}, check_mode=True
        )
        assert r.changed is True
        assert (await mgr.get())["enabled"] == before["enabled"]


class TestKeaService:
    async def test_status(self, opn_client: OpnsenseClient) -> None:
        assert await KeaServiceManager(opn_client).status() in {
            "running",
            "stopped",
            "disabled",
            "unknown",
        }
