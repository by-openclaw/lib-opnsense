# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.monit.settings.MonitSettingsManager.

Singleton pattern: the Monit ``settings/get`` document nests the daemon config
under ``general``; the manager unwraps it for diffing and re-nests on POST.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError
from opnsense.managers.monit.settings import MonitSettingsManager


@pytest.mark.asyncio
class TestGet:
    async def test_get_unwraps_general(self, mock_client: AsyncMock) -> None:
        """get() unwraps the 'general' block from the settings payload."""
        mock_client.get.return_value = {
            "monit": {"general": {"enabled": "0", "port": "25"}},
        }
        mgr = MonitSettingsManager(mock_client)
        result = await mgr.get()
        assert result == {"enabled": "0", "port": "25"}
        mock_client.get.assert_awaited_once_with("monit/settings/get")

    async def test_get_returns_empty_when_no_general(self, mock_client: AsyncMock) -> None:
        """get() returns {} when 'general' is missing."""
        mock_client.get.return_value = {"monit": {}}
        mgr = MonitSettingsManager(mock_client)
        assert await mgr.get() == {}


@pytest.mark.asyncio
class TestEnsure:
    async def test_noop_when_already_matches(self, mock_client: AsyncMock) -> None:
        """ensure present with no drift -> noop, no POST."""
        mock_client.get.return_value = {
            "monit": {"general": {"enabled": "0", "port": "25"}},
        }
        mgr = MonitSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "0"})
        assert result.changed is False
        assert result.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_updates_when_drifted_and_nests_general(self, mock_client: AsyncMock) -> None:
        """ensure present with drift -> POST body nests params under 'general'."""
        mock_client.get.side_effect = [
            {"monit": {"general": {"enabled": "0", "port": "25"}}},
            {"monit": {"general": {"enabled": "1", "port": "25"}}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "1"})

        assert result.changed is True
        assert result.action == "updated"
        mock_client.post.assert_awaited_once_with(
            "monit/settings/set",
            {"monit": {"general": {"enabled": "1"}}},
        )
        mock_client.reconfigure.assert_awaited_once_with("monit/service/reconfigure", timeout=60)

    async def test_check_mode_no_post(self, mock_client: AsyncMock) -> None:
        """check_mode update -> changed=True but no POST/reconfigure."""
        mock_client.get.return_value = {
            "monit": {"general": {"enabled": "0", "port": "25"}},
        }
        mgr = MonitSettingsManager(mock_client)
        result = await mgr.ensure("present", {"enabled": "1"}, check_mode=True)
        assert result.changed is True
        assert result.action == "updated"
        mock_client.post.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_absent_raises_value_error(self, mock_client: AsyncMock) -> None:
        """Singleton managers reject state='absent'."""
        mgr = MonitSettingsManager(mock_client)
        with pytest.raises(ValueError):
            await mgr.ensure("absent", {"enabled": "0"})


@pytest.mark.asyncio
class TestValidation:
    async def test_invalid_sslversion_raises(self, mock_client: AsyncMock) -> None:
        """Invalid sslversion enum raises FieldValidationError before any call."""
        mgr = MonitSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"sslversion": "SSLV3"})
        mock_client.get.assert_not_awaited()
        mock_client.post.assert_not_awaited()

    async def test_invalid_enabled_bool_str_raises(self, mock_client: AsyncMock) -> None:
        """Non bool_str 'enabled' raises FieldValidationError before any call."""
        mgr = MonitSettingsManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"enabled": "true"})
        mock_client.post.assert_not_awaited()


class TestRedactFields:
    def test_redact_fields_defined(self) -> None:
        """Secrets and PII fields are redacted."""
        for field in ("password", "httpdPassword", "username", "httpdUsername", "mmonitUrl"):
            assert field in MonitSettingsManager.REDACT_FIELDS


@pytest.mark.asyncio
class TestRedaction:
    async def test_password_redacted_in_after(self, mock_client: AsyncMock) -> None:
        """password is redacted in the before/after dicts."""
        mock_client.get.side_effect = [
            {"monit": {"general": {"enabled": "0", "password": "old"}}},
            {"monit": {"general": {"enabled": "0", "password": "s3cret"}}},
        ]
        mock_client.post.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitSettingsManager(mock_client)
        result = await mgr.ensure("present", {"password": "s3cret"})

        assert result.after is not None
        assert result.after["password"] == "<REDACTED:password>"
