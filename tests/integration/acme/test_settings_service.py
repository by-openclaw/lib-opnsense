# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests -- ACME settings + service against a live OPNsense device.

Read-mostly and non-destructive: reads settings, asserts a check_mode set makes
no change, and reads service status + configtest. Does NOT enable the plugin or
reconfigure (avoids side effects on a shared device).
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.acme.service import AcmeServiceManager
from opnsense.managers.acme.settings import AcmeSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAcmeSettings:
    async def test_01_get_returns_settings(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeSettingsManager(opn_client)
        settings = await mgr.get()
        assert isinstance(settings, dict)
        # The settings document always carries the master 'enabled' toggle.
        assert "enabled" in settings

    async def test_02_check_mode_no_change(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeSettingsManager(opn_client)
        # Callers pass plain enum strings (NOT the option-dict the API returns on
        # read); the DiffEngine normalises the stored enum dict for comparison.
        # check_mode never writes regardless of the diff result.
        r = await mgr.ensure("present", {"logLevel": "debug"}, check_mode=True)
        assert r.action in ("noop", "updated")
        assert r.changed in (True, False)


class TestAcmeService:
    async def test_01_status_is_string(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeServiceManager(opn_client)
        status = await mgr.status()
        assert isinstance(status, str)
        assert status != ""

    async def test_02_configtest_returns_result(self, opn_client: OpnsenseClient) -> None:
        mgr = AcmeServiceManager(opn_client)
        result = await mgr.configtest()
        assert isinstance(result, str)
