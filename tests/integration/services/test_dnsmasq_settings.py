# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Dnsmasq settings against a live OPNsense device.

Safety boundaries (critical — read before running):
    - Dnsmasq holds 67/547 globally when ``strictbind='0'`` (the default
      pre-OPNsense-26.1 behaviour), which collides with Kea-DHCP on those
      ports. This suite must NOT enable Dnsmasq on a Kea-running device.
    - All write tests issue ``enable='0'`` only — they assert noop on a
      device where dnsmasq is already disabled, OR safely turn it off if
      it is on (with cleanup restoring the original state).
    - The test snapshots dnsmasq settings at start and restores them at end.
    - For a fresh FW where dnsmasq is on by default, set
      ``OPN_DNSMASQ_TEST_ALLOW_TOGGLE=1`` to enable the toggle test that
      actually flips enable to '0'.
"""

from __future__ import annotations

import os

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.services.dnsmasq_settings import DnsmasqSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_ALLOW_TOGGLE = os.environ.get("OPN_DNSMASQ_TEST_ALLOW_TOGGLE") == "1"


class TestDnsmasqSettingsReadOnly:
    """Always-safe checks — read + idempotent ensure to current state."""

    async def test_01_get_returns_known_fields(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqSettingsManager(opn_client)
        settings = await mgr.get()
        assert "enable" in settings, "dnsmasq settings missing 'enable' field"
        assert settings["enable"] in ("0", "1"), f"unexpected enable value: {settings['enable']!r}"

    async def test_02_ensure_current_enable_is_noop(self, opn_client: OpnsenseClient) -> None:
        """Setting enable to its current value must noop."""
        mgr = DnsmasqSettingsManager(opn_client)
        current = (await mgr.get()).get("enable", "0")
        r = await mgr.ensure("present", {"enable": current})
        assert r.action == "noop"
        assert r.changed is False

    async def test_03_check_mode_does_not_modify(self, opn_client: OpnsenseClient) -> None:
        """check_mode=True must never touch the live config."""
        mgr = DnsmasqSettingsManager(opn_client)
        before = await mgr.get()
        await mgr.ensure(
            "present",
            {"enable": "0" if before.get("enable") == "1" else "1"},
            check_mode=True,
        )
        after = await mgr.get()
        assert after.get("enable") == before.get("enable")


class TestDnsmasqSettingsValidation:
    """Validation errors must surface before any API call."""

    async def test_invalid_bool_rejected(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqSettingsManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"enable": "not-a-bool"})

    async def test_invalid_add_mac_rejected(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqSettingsManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"add_mac": "bogus"})


@pytest.mark.skipif(
    not _ALLOW_TOGGLE,
    reason="set OPN_DNSMASQ_TEST_ALLOW_TOGGLE=1 to test actual enable toggle",
)
class TestDnsmasqSettingsToggle:
    """Opt-in: flip enable. Restores original state in cleanup."""

    async def test_disable_then_restore(self, opn_client: OpnsenseClient) -> None:
        mgr = DnsmasqSettingsManager(opn_client)
        original = (await mgr.get()).get("enable", "0")
        try:
            await mgr.ensure("present", {"enable": "0"})
            assert (await mgr.get()).get("enable") == "0"
        finally:
            await mgr.ensure("present", {"enable": original})
            assert (await mgr.get()).get("enable") == original
