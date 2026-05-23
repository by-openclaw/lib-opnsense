# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Dnsmasq service controller against a live OPNsense device.

Safety boundaries:
    - Read-only ``status`` + idempotent ``ensure(current_state)`` are always
      safe (always noop).
    - The lifecycle tests (start/stop transitions) are gated behind
      ``OPN_DNSMASQ_TEST_ALLOW_LIFECYCLE=1`` because starting dnsmasq on a
      Kea-running device collides on UDP/547.
"""

from __future__ import annotations

import os

import pytest

from opnsense.client import OpnsenseClient
from opnsense.managers.services.dnsmasq_service import DnsmasqServiceManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_ALLOW_LIFECYCLE = os.environ.get("OPN_DNSMASQ_TEST_ALLOW_LIFECYCLE") == "1"


class TestDnsmasqServiceReadOnly:
    async def test_status_returns_known_value(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqServiceManager(opn_client)
        result = await mgr.status()
        assert result in ("running", "stopped", "disabled", "unknown"), (
            f"unexpected dnsmasq status: {result!r}"
        )

    async def test_ensure_current_state_is_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqServiceManager(opn_client)
        current = await mgr.status()
        target = "running" if current == "running" else "stopped"
        r = await mgr.ensure(target)
        assert r.action == "noop"
        assert r.changed is False


@pytest.mark.skipif(
    not _ALLOW_LIFECYCLE,
    reason="set OPN_DNSMASQ_TEST_ALLOW_LIFECYCLE=1 to test start/stop (collides with Kea on 547)",
)
class TestDnsmasqServiceLifecycle:
    async def test_restore_after_toggle(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqServiceManager(opn_client)
        original = await mgr.status()
        try:
            target = "stopped" if original == "running" else "running"
            await mgr.ensure(target)
            assert (await mgr.status()) == target
        finally:
            await mgr.ensure(original if original in ("running", "stopped") else "stopped")
