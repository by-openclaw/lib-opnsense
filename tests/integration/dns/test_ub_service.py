# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Unbound service controller against a live OPNsense device.

Safety boundaries:
    - ``status`` is read-only.
    - ``ensure('reconfigured')`` re-reads the current config — harmless on a
      running resolver and a no-op daemon-wise while it is disabled.
    - start/stop are never issued (they would interrupt the device's DNS).
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.dns.ub_service import UbServiceManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestUbServiceReadOnly:
    async def test_01_status_is_a_known_value(self, opn_client: OpnsenseClient) -> None:
        mgr = UbServiceManager(opn_client)
        status = await mgr.status()
        assert status in {"running", "stopped", "disabled", "unknown"}, status

    async def test_02_ensure_current_state_is_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = UbServiceManager(opn_client)
        status = await mgr.status()
        target = "running" if status == "running" else "stopped"
        r = await mgr.ensure(target)
        assert r.action == "noop"
        assert r.changed is False

    async def test_03_reconfigure_reports_action(self, opn_client: OpnsenseClient) -> None:
        mgr = UbServiceManager(opn_client)
        r = await mgr.ensure("reconfigured")
        assert r.action == "reconfigured"
