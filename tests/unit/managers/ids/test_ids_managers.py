# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests — IdsSettingsManager, IdsRulesetManager, IdsServiceManager, mDNS repeater managers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.ids.ruleset import IdsRulesetManager
from opnsense.managers.ids.service import IdsServiceManager
from opnsense.managers.ids.settings import IdsSettingsManager
from opnsense.managers.services.mdnsrepeater_service import MdnsRepeaterServiceManager
from opnsense.managers.services.mdnsrepeater_settings import MdnsRepeaterSettingsManager

ROWS = {
    "rows": [
        {"filename": "emerging-malware.rules", "enabled": "0"},
        {"filename": "abuse.ch.sslblacklist.rules", "enabled": "1"},
    ]
}


@pytest.mark.asyncio
class TestIdsSettings:
    async def test_enable_posts_general_and_reconfigures(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"ids": {"general": {"enabled": "0", "interfaces": {}}}},
            {"ids": {"general": {"enabled": "1"}}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await IdsSettingsManager(mock_client).ensure(
            "present",
            {
                "enabled": "1",
                "mode": "pcap",
                "interfaces": ["opt12"],
                "homenet": ["10.1.0.0/16", "fd01::/32"],
            },
        )
        assert r.changed is True
        mock_client.post.assert_awaited_once_with(
            "ids/settings/set",
            {
                "ids": {
                    "general": {
                        "enabled": "1",
                        "mode": "pcap",
                        "interfaces": "opt12",
                        "homenet": "10.1.0.0/16,fd01::/32",
                    }
                }
            },
        )
        mock_client.reconfigure.assert_awaited_once_with("ids/service/reconfigure", timeout=120)

    async def test_mode_enum(self, mock_client: AsyncMock) -> None:
        with pytest.raises(FieldValidationError):
            await IdsSettingsManager(mock_client).ensure("present", {"mode": "ips"})


@pytest.mark.asyncio
class TestIdsRuleset:
    async def test_noop_when_flags_match(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = ROWS
        r = await IdsRulesetManager(mock_client).ensure_many(
            {"abuse.ch.sslblacklist.rules": True, "emerging-malware.rules": False}
        )
        assert r.action == "noop" and r.before == {
            "abuse.ch.sslblacklist.rules": "1",
            "emerging-malware.rules": "0",
        }
        mock_client.post.assert_not_awaited()

    async def test_toggle_only_the_drifted_and_reconfigure(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = ROWS
        mock_client.post.return_value = {"status": "ok"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await IdsRulesetManager(mock_client).ensure_many(
            {"emerging-malware.rules": True, "abuse.ch.sslblacklist.rules": True}
        )
        assert r.changed is True and r.after["emerging-malware.rules"] == "1"
        mock_client.post.assert_awaited_once_with(
            "ids/settings/toggleRuleset/emerging-malware.rules/1", data={}
        )
        mock_client.reconfigure.assert_awaited_once_with("ids/service/reconfigure", timeout=120)

    async def test_check_mode_and_unknown(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = ROWS
        r = await IdsRulesetManager(mock_client).ensure(
            "emerging-malware.rules", True, check_mode=True
        )
        assert r.changed is True
        mock_client.post.assert_not_awaited()
        with pytest.raises(ValueError):
            await IdsRulesetManager(mock_client).ensure("nope.rules", True)


@pytest.mark.asyncio
class TestIdsService:
    async def test_update_rules_and_status(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "disabled"}
        mock_client.post.return_value = {"status": "ok"}
        svc = IdsServiceManager(mock_client)
        assert await svc.status() == "disabled"
        await svc.update_rules()
        mock_client.post.assert_awaited_once_with("ids/service/updateRules", data={}, timeout=600)


@pytest.mark.asyncio
class TestMdnsRepeater:
    async def test_settings_and_service(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"mdnsrepeater": {"enabled": "0", "interfaces": {}}},
            {"mdnsrepeater": {"enabled": "1"}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await MdnsRepeaterSettingsManager(mock_client).ensure(
            "present", {"enabled": "1", "interfaces": ["opt2", "opt8"]}
        )
        assert r.changed is True
        mock_client.post.assert_awaited_once_with(
            "mdnsrepeater/settings/set",
            {"mdnsrepeater": {"enabled": "1", "interfaces": "opt2,opt8"}},
        )
        mock_client.get.side_effect = None
        mock_client.get.return_value = {"status": "running"}
        assert await MdnsRepeaterServiceManager(mock_client).status() == "running"
        mock_client.get.assert_awaited_with("mdnsrepeater/service/status")
