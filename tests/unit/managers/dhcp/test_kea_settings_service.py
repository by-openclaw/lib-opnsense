# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests — Kea4/Kea6 general settings singletons + Kea service controller."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.dhcp.kea4_settings import Kea4SettingsManager
from opnsense.managers.dhcp.kea6_settings import Kea6SettingsManager
from opnsense.managers.dhcp.kea_service import KeaServiceManager

CASES = [
    (Kea4SettingsManager, "kea/dhcpv4", "dhcpv4", "compatibility"),
    (Kea6SettingsManager, "kea/dhcpv6", "dhcpv6", "mac_sources"),
]
IDS = ["kea4", "kea6"]


def _doc(payload, general):
    return {payload: {"general": general, "ha": {}}}


@pytest.mark.asyncio
@pytest.mark.parametrize("cls,endpoint,payload,multi", CASES, ids=IDS)
class TestKeaSettings:
    async def test_get_unwraps_general(self, mock_client: AsyncMock, cls, endpoint, payload, multi):
        mock_client.get.return_value = _doc(payload, {"enabled": "0"})
        assert await cls(mock_client).get() == {"enabled": "0"}
        mock_client.get.assert_awaited_once_with(f"{endpoint}/get")

    async def test_enable_with_interfaces_posts_nested(
        self, mock_client: AsyncMock, cls, endpoint, payload, multi
    ):
        mock_client.get.side_effect = [
            _doc(payload, {"enabled": "0", "interfaces": {}}),
            _doc(payload, {"enabled": "1"}),
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        r = await cls(mock_client).ensure(
            "present", {"enabled": "1", "interfaces": ["opt2", "opt3"]}
        )
        assert r.changed is True
        mock_client.post.assert_awaited_once_with(
            f"{endpoint}/set", {payload: {"general": {"enabled": "1", "interfaces": "opt2,opt3"}}}
        )
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_matching(self, mock_client: AsyncMock, cls, endpoint, payload, multi):
        mock_client.get.return_value = _doc(payload, {"enabled": "1", "valid_lifetime": "4000"})
        r = await cls(mock_client).ensure("present", {"enabled": "1", "valid_lifetime": "4000"})
        assert r.action == "noop"

    async def test_invalid_bool(self, mock_client: AsyncMock, cls, endpoint, payload, multi):
        with pytest.raises(FieldValidationError):
            await cls(mock_client).ensure("present", {"enabled": "yes"})


@pytest.mark.asyncio
class TestKea4Enum:
    async def test_socket_type_enum(self, mock_client: AsyncMock) -> None:
        with pytest.raises(FieldValidationError):
            await Kea4SettingsManager(mock_client).ensure("present", {"dhcp_socket_type": "tcp"})


@pytest.mark.asyncio
class TestKeaService:
    async def test_status_and_reconfigure(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"status": "disabled"}
        mgr = KeaServiceManager(mock_client)
        assert await mgr.status() == "disabled"
        mock_client.get.assert_awaited_with("kea/service/status")
        mock_client.get.return_value = {"status": "running"}
        mock_client.post.return_value = {"status": "ok"}
        assert (await mgr.ensure("reconfigured")).action == "reconfigured"
        mock_client.post.assert_awaited_once_with("kea/service/reconfigure", {}, timeout=60)
