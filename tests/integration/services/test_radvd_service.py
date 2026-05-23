# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — radvd service controller against a live OPNsense device.

Safety boundaries:
    - This suite reads service status and performs an idempotent ``ensure``
      call to whatever state the daemon is currently in (so no actual
      state transition occurs).
    - It does NOT call ``start``, ``stop``, or ``reconfigure`` directly on a
      production device unless the user explicitly opts in via the env var
      ``OPN_RADVD_ALLOW_START=1``. Without that env var, only safe read +
      idempotent ensure-noop paths are exercised.
"""

from __future__ import annotations

import os

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.radvd_service import RadvdServiceManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_ALLOW_START = os.environ.get("OPN_RADVD_ALLOW_START") == "1"


class TestRadvdServiceReadOnly:
    """Read-only checks — always safe to run."""

    async def test_status_returns_known_value(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdServiceManager(opn_client)
        result = await mgr.status()
        assert result in ("running", "stopped", "disabled", "unknown"), (
            f"unexpected radvd status: {result!r}"
        )

    async def test_ensure_current_state_is_noop(self, opn_client: OpnsenseClient) -> None:
        """ensure() to the current state should be a noop transition."""
        mgr = RadvdServiceManager(opn_client)
        current = await mgr.status()
        target = "running" if current == "running" else "stopped"
        r = await mgr.ensure(target)
        assert r.action == "noop", f"expected noop for {target} (current={current})"
        assert r.changed is False


@pytest.mark.skipif(
    not _ALLOW_START,
    reason="set OPN_RADVD_ALLOW_START=1 to enable lifecycle tests (modifies live service)",
)
class TestRadvdServiceLifecycle:
    """Service lifecycle — disabled by default (modifies a live daemon)."""

    async def test_start_then_stop(self, opn_client: OpnsenseClient) -> None:
        mgr = RadvdServiceManager(opn_client)
        original = await mgr.status()
        try:
            await mgr.ensure("running")
            assert (await mgr.status()) == "running"
        finally:
            # Restore previous state
            if original != "running":
                await mgr.ensure("stopped")
