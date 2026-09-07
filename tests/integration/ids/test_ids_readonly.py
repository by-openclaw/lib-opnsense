# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Integration tests — IDS + mDNS repeater managers, READ-ONLY / reversible.

Safety: settings noop + check_mode only; the ruleset test toggles the harmless
``opnsense.test.rules`` set on and back off without downloading rules; services: status only.
"""

from __future__ import annotations

import pytest

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseError
from opnsense.managers.ids.ruleset import IdsRulesetManager
from opnsense.managers.ids.service import IdsServiceManager
from opnsense.managers.ids.settings import IdsSettingsManager
from opnsense.managers.services.mdnsrepeater_service import MdnsRepeaterServiceManager
from opnsense.managers.services.mdnsrepeater_settings import MdnsRepeaterSettingsManager

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestIds:
    async def test_01_settings_noop_and_check_mode(self, opn_client: OpnsenseClient) -> None:
        mgr = IdsSettingsManager(opn_client)
        cur = await mgr.get()
        assert (await mgr.ensure("present", {"enabled": cur["enabled"]})).action == "noop"
        r = await mgr.ensure(
            "present", {"enabled": "0" if cur["enabled"] == "1" else "1"}, check_mode=True
        )
        assert r.changed is True and (await mgr.get())["enabled"] == cur["enabled"]

    async def test_02_ruleset_toggle_roundtrip(self, opn_client: OpnsenseClient) -> None:
        mgr = IdsRulesetManager(opn_client)
        rows = {r["filename"]: r["enabled"] for r in await mgr.list()}
        assert "opnsense.test.rules" in rows
        original = rows["opnsense.test.rules"] == "1"
        try:
            try:
                r = await mgr.ensure("opnsense.test.rules", not original, apply=False)
            except OpnsenseError as exc:
                if "IDS model may be invalid" in str(exc):
                    pytest.skip(f"device precondition: {exc}")
                raise
            assert r.changed is True
            assert (
                await mgr.ensure("opnsense.test.rules", not original, apply=False)
            ).action == "noop"
        finally:
            await mgr.ensure("opnsense.test.rules", original, apply=False)

    async def test_03_service_status(self, opn_client: OpnsenseClient) -> None:
        assert await IdsServiceManager(opn_client).status() in {
            "running",
            "stopped",
            "disabled",
            "unknown",
        }


class TestMdnsRepeater:
    async def test_01_settings_noop(self, opn_client: OpnsenseClient) -> None:
        mgr = MdnsRepeaterSettingsManager(opn_client)
        try:
            cur = await mgr.get()
        except OpnsenseError as exc:
            pytest.skip(f"os-mdns-repeater not installed: {exc}")
        assert (await mgr.ensure("present", {"enabled": cur["enabled"]})).action == "noop"

    async def test_02_service_status(self, opn_client: OpnsenseClient) -> None:
        try:
            status = await MdnsRepeaterServiceManager(opn_client).status()
        except OpnsenseError as exc:
            pytest.skip(f"os-mdns-repeater not installed: {exc}")
        assert status in {"running", "stopped", "disabled", "unknown"}
