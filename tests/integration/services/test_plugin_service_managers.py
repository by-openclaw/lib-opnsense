# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — plugin service controllers (chrony, lldpd, qemu-guest-agent,
dnscrypt-proxy) against a live OPNsense device.

Safety boundaries: status (read-only), ensure-to-current-state (noop), reconfigure (re-reads the
current config). start/stop are never issued. Missing plugin -> skip.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseError
from opnsense.managers.dns.dnscrypt_service import DnscryptProxyServiceManager
from opnsense.managers.services.chrony_service import ChronyServiceManager
from opnsense.managers.services.lldpd_service import LldpdServiceManager
from opnsense.managers.services.qemuguestagent_service import QemuGuestAgentServiceManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

CASES = [
    ChronyServiceManager,
    LldpdServiceManager,
    QemuGuestAgentServiceManager,
    DnscryptProxyServiceManager,
]
IDS = ["chrony", "lldpd", "qemuguestagent", "dnscrypt"]


async def _status_or_skip(mgr):
    try:
        return await mgr.status()
    except OpnsenseError as exc:
        pytest.skip(f"{type(mgr).__name__}: plugin endpoint unavailable ({exc})")


@pytest.mark.parametrize("cls", CASES, ids=IDS)
class TestPluginServiceReadOnly:
    async def test_01_status_known_value(self, opn_client: OpnsenseClient, cls) -> None:
        assert await _status_or_skip(cls(opn_client)) in {
            "running",
            "stopped",
            "disabled",
            "unknown",
        }

    async def test_02_ensure_current_state_is_noop(self, opn_client: OpnsenseClient, cls) -> None:
        mgr = cls(opn_client)
        status = await _status_or_skip(mgr)
        r = await mgr.ensure("running" if status == "running" else "stopped")
        assert r.action == "noop" and r.changed is False

    async def test_03_reconfigure_reports_action(self, opn_client: OpnsenseClient, cls) -> None:
        mgr = cls(opn_client)
        await _status_or_skip(mgr)
        assert (await mgr.ensure("reconfigured")).action == "reconfigured"
