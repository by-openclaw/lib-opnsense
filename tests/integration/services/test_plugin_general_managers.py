# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — plugin general settings (chrony, lldpd, qemu-guest-agent, dnscrypt-proxy)
against a live OPNsense device.

Safety boundaries:
    - read + ensure-to-current-value (noop) + check_mode only — never flips ``enabled``.
    - a device without one of the plugins skips that manager (404 on get).
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError, OpnsenseEndpointMissingError, OpnsenseError
from opnsense.managers.dns.dnscrypt_general import DnscryptProxyGeneralManager
from opnsense.managers.services.chrony_general import ChronyGeneralManager
from opnsense.managers.services.lldpd_general import LldpdGeneralManager
from opnsense.managers.services.qemuguestagent_settings import QemuGuestAgentSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

CASES = [
    (ChronyGeneralManager, "enabled"),
    (LldpdGeneralManager, "enabled"),
    (QemuGuestAgentSettingsManager, "Enabled"),
    (DnscryptProxyGeneralManager, "enabled"),
]
IDS = ["chrony", "lldpd", "qemuguestagent", "dnscrypt"]


async def _settings_or_skip(mgr):
    try:
        return await mgr.get()
    except (OpnsenseEndpointMissingError, OpnsenseError) as exc:  # plugin not installed
        pytest.skip(f"{type(mgr).__name__}: plugin endpoint unavailable ({exc})")


@pytest.mark.parametrize("cls,enable", CASES, ids=IDS)
class TestPluginGeneralReadOnly:
    async def test_01_get_returns_enable_flag(
        self, opn_client: OpnsenseClient, cls, enable
    ) -> None:
        settings = await _settings_or_skip(cls(opn_client))
        assert settings.get(enable) in ("0", "1"), f"unexpected {enable}: {settings.get(enable)!r}"

    async def test_02_ensure_current_is_noop(self, opn_client: OpnsenseClient, cls, enable) -> None:
        mgr = cls(opn_client)
        cur = await _settings_or_skip(mgr)
        r = await mgr.ensure("present", {enable: cur[enable]})
        assert r.action == "noop" and r.changed is False

    async def test_03_check_mode_does_not_modify(
        self, opn_client: OpnsenseClient, cls, enable
    ) -> None:
        mgr = cls(opn_client)
        before = await _settings_or_skip(mgr)
        r = await mgr.ensure(
            "present", {enable: "0" if before[enable] == "1" else "1"}, check_mode=True
        )
        assert r.changed is True
        assert (await mgr.get())[enable] == before[enable]

    async def test_04_invalid_bool_rejected(self, opn_client: OpnsenseClient, cls, enable) -> None:
        with pytest.raises(FieldValidationError):
            await cls(opn_client).ensure("present", {enable: "not-a-bool"})
