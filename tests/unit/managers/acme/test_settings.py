# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.settings.AcmeSettingsManager.

Singleton: the ``settings/get`` document nests config under ``settings``; the
manager unwraps it for diffing and re-nests on POST under
``{"acmeclient": {"settings": {...}}}``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.acme.settings import AcmeSettingsManager


@pytest.mark.asyncio
class TestGet:
    async def test_get_unwraps_settings(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "acmeclient": {"settings": {"enabled": "0", "autoRenewal": "1"}},
        }
        mgr = AcmeSettingsManager(mock_client)
        result = await mgr.get()
        assert result == {"enabled": "0", "autoRenewal": "1"}
        mock_client.get.assert_awaited_once_with("acmeclient/settings/get")

    async def test_get_returns_empty_when_no_settings(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {"acmeclient": {}}
        mgr = AcmeSettingsManager(mock_client)
        assert await mgr.get() == {}


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_matches(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "acmeclient": {"settings": {"enabled": "0", "autoRenewal": "1"}},
        }
        mgr = AcmeSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "0"})
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_update_nests_settings_and_reconfigures(self, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = [
            {"acmeclient": {"settings": {"enabled": "0", "autoRenewal": "1"}}},
            {"acmeclient": {"settings": {"enabled": "1", "autoRenewal": "1"}}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}
        mgr = AcmeSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "1"})
        assert result.changed is True
        assert result.action == "updated"
        mock_client.post.assert_awaited_once_with(
            "acmeclient/settings/set",
            {"acmeclient": {"settings": {"enabled": "1"}}},
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "acmeclient/service/reconfigure", timeout=60
        )

    async def test_check_mode_no_post(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "acmeclient": {"settings": {"enabled": "0"}},
        }
        mgr = AcmeSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "1"}, check_mode=True)
        assert result.changed is True
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_absent_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeSettingsManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("absent", {"enabled": "0"})


@pytest.mark.asyncio
class TestValidation:
    async def test_invalid_loglevel_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"logLevel": "trace"})
        mock_client.post.assert_not_awaited()

    async def test_invalid_environment_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"environment": "qa"})
