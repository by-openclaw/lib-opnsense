# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — Unbound general settings against a live OPNsense device.

Safety boundaries (critical — read before running):
    - Unbound is the device's resolver. This suite never flips ``enabled``
      unless ``OPN_UNBOUND_TEST_ALLOW_TOGGLE=1`` is set, and then restores the
      original value in cleanup.
    - The default tests are read + idempotent ensure-to-current + check_mode,
      which never modify the live config.
"""

from __future__ import annotations

import os

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import FieldValidationError
from opnsense.managers.dns.ub_settings import UbSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_ALLOW_TOGGLE = os.environ.get("OPN_UNBOUND_TEST_ALLOW_TOGGLE") == "1"


class TestUbSettingsReadOnly:
    """Always-safe checks — read + idempotent ensure to current state."""

    async def test_01_get_returns_general_block(self, opn_client: OpnsenseClient) -> None:
        mgr = UbSettingsManager(opn_client)
        settings = await mgr.get()
        assert settings.get("enabled") in ("0", "1"), f"unexpected: {settings.get('enabled')!r}"
        assert "port" in settings
        assert "advanced" not in settings, "section unwrap failed — advanced block leaked"

    async def test_02_ensure_current_values_is_noop(self, opn_client: OpnsenseClient) -> None:
        """Re-asserting enabled/port/local_zone_type to their live values must noop."""
        mgr = UbSettingsManager(opn_client)
        cur = await mgr.get()
        lzt = cur.get("local_zone_type")
        selected = (
            next((k for k, v in lzt.items() if isinstance(v, dict) and v.get("selected")), "")
            if isinstance(lzt, dict)
            else str(lzt)
        )
        r = await mgr.ensure(
            "present",
            {"enabled": cur["enabled"], "port": cur["port"], "local_zone_type": selected},
        )
        assert r.action == "noop"
        assert r.changed is False

    async def test_03_multi_select_current_selection_is_noop(
        self, opn_client: OpnsenseClient
    ) -> None:
        """Passing the currently selected interface list (any order) must noop."""
        mgr = UbSettingsManager(opn_client)
        cur = await mgr.get()
        raw = cur.get("active_interface", {})
        selected = (
            [k for k, v in raw.items() if isinstance(v, dict) and v.get("selected")]
            if isinstance(raw, dict)
            else [x for x in str(raw).split(",") if x]
        )
        r = await mgr.ensure("present", {"active_interface": list(reversed(selected))})
        assert r.action == "noop", f"multi-select not idempotent: {r}"

    async def test_04_check_mode_does_not_modify(self, opn_client: OpnsenseClient) -> None:
        mgr = UbSettingsManager(opn_client)
        before = await mgr.get()
        r = await mgr.ensure(
            "present",
            {"enabled": "0" if before.get("enabled") == "1" else "1"},
            check_mode=True,
        )
        assert r.changed is True
        after = await mgr.get()
        assert after.get("enabled") == before.get("enabled")


class TestUbSettingsValidation:
    """Validation errors must surface before any API call."""

    async def test_invalid_bool_rejected(self, opn_client: OpnsenseClient) -> None:
        mgr = UbSettingsManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"enabled": "not-a-bool"})

    async def test_invalid_local_zone_type_rejected(self, opn_client: OpnsenseClient) -> None:
        mgr = UbSettingsManager(opn_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"local_zone_type": "bogus"})


@pytest.mark.skipif(
    not _ALLOW_TOGGLE,
    reason="set OPN_UNBOUND_TEST_ALLOW_TOGGLE=1 to test the actual enable toggle",
)
class TestUbSettingsToggle:
    """Opt-in: flip enabled. Restores original state in cleanup."""

    async def test_toggle_then_restore(self, opn_client: OpnsenseClient) -> None:
        mgr = UbSettingsManager(opn_client)
        original = (await mgr.get()).get("enabled", "0")
        target = "0" if original == "1" else "1"
        try:
            r = await mgr.ensure("present", {"enabled": target})
            assert r.changed is True and r.action == "updated"
            assert (await mgr.get()).get("enabled") == target
            assert (await mgr.ensure("present", {"enabled": target})).action == "noop"
        finally:
            await mgr.ensure("present", {"enabled": original})
            assert (await mgr.get()).get("enabled") == original
