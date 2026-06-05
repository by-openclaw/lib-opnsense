# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — MonitSettingsManager singleton against a live OPNsense device.

Requirements:
    - Live OPNsense device accessible via OPN_HOST, OPN_KEY, OPN_SECRET env vars
    - API user must have full admin privileges
    - Run with: pytest tests/integration/monit/test_settings.py -v

Test flow (ordered, conservative — singleton):
    1. Read (R)         -- TestMonitSettings.test_01_read
    2. Idempotent (I)   -- TestMonitSettings.test_02_ensure_current_is_noop
    3. Enabled noop (N) -- TestMonitSettings.test_03_ensure_enabled_noop

Notes:
    This is a LIVE singleton (the Monit daemon config). The flow is read +
    noop oriented and MUST NOT leave the daemon config altered. We read the
    current ``general`` block via the manager and re-ensure the *current*
    values, which must diff to ``noop``. We do not write any new value.

Naming convention:
    No objects are created — singleton config only.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.monit.settings import MonitSettingsManager
from opnsense.models.base import EnsureResult

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestMonitSettings:
    """Read + noop-oriented checks for the Monit global settings singleton."""

    async def test_01_read(self, opn_client: OpnsenseClient) -> None:
        """The current settings block reads back as a dict."""
        mgr = MonitSettingsManager(opn_client)
        current = await mgr.get()
        assert isinstance(current, dict)

    async def test_02_ensure_current_is_noop(self, opn_client: OpnsenseClient) -> None:
        """Re-ensuring the exact current ``enabled`` value diffs to noop.

        Reading the live value first guarantees we never change the daemon
        config — we assert against whatever the device currently reports.
        """
        mgr = MonitSettingsManager(opn_client)
        current = await mgr.get()
        if "enabled" not in current:
            pytest.skip("device did not report an 'enabled' value to re-ensure")

        r = await mgr.ensure("present", {"enabled": current["enabled"]})
        assert isinstance(r, EnsureResult)
        assert r.changed is False
        assert r.action == "noop"

    async def test_03_ensure_enabled_noop(self, opn_client: OpnsenseClient) -> None:
        """``ensure(present, {"enabled": "1"})`` does not error and returns a result.

        Monit is enabled in our baseline, so this is expected to diff to noop.
        If the device reports it disabled we skip rather than flip it on (we
        must not leave the daemon config altered).
        """
        mgr = MonitSettingsManager(opn_client)
        current = await mgr.get()
        if current.get("enabled") != "1":
            pytest.skip("Monit not enabled on this device — skip to avoid altering config")

        r = await mgr.ensure("present", {"enabled": "1"})
        assert isinstance(r, EnsureResult)
        assert r.changed is False
        assert r.action == "noop"
