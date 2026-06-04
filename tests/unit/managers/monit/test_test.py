# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.monit.test.MonitTestManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseError
from opnsense.managers.monit.test import MonitTestManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_test(self, mock_client: AsyncMock) -> None:
        """ensure present when test does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitTestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "CPUUsage90",
                "type": "SystemResource",
                "condition": "cpu usage is greater than 90%",
                "action": "alert",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("monit/service/reconfigure", timeout=None)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when test exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "CPUUsage90", "condition": "cpu usage > 90%"},
        ]

        mgr = MonitTestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "CPUUsage90", "condition": "cpu usage > 90%"},
        )

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-existing"
        mock_client.create.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when test condition differs -> update + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "CPUUsage90", "condition": "cpu usage > 90%"},
        ]
        mock_client.get.return_value = {
            "test": {"uuid": "uuid-existing", "name": "CPUUsage90", "condition": "cpu usage > 90%"},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitTestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "CPUUsage90", "condition": "cpu usage > 95%"},
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.update.assert_awaited_once()


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_test(self, mock_client: AsyncMock) -> None:
        """ensure absent when test exists -> delete + reconfigure."""
        mock_client.search.return_value = [{"uuid": "uuid-existing", "name": "CPUUsage90"}]
        mock_client.get.return_value = {"test": {"uuid": "uuid-existing", "name": "CPUUsage90"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitTestManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "CPUUsage90"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when test does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = MonitTestManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "gone"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no API calls."""
        mock_client.search.return_value = []

        mgr = MonitTestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "Ping1", "type": "NetworkPing"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestEndpointSuffix:
    """Tests for Test entity suffix."""

    async def test_search_uses_search_test(self, mock_client: AsyncMock) -> None:
        """list() calls search endpoint with Test suffix."""
        mock_client.search.return_value = []

        mgr = MonitTestManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with("monit/settings/searchTest", search_phrase="")

    async def test_create_uses_add_test(self, mock_client: AsyncMock) -> None:
        """create() calls add endpoint with Test suffix and payload key."""
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = MonitTestManager(mock_client)
        await mgr.create(params={"name": "Ping1", "type": "NetworkPing"})

        mock_client.create.assert_awaited_once_with(
            "monit/settings/addTest", "test", {"name": "Ping1", "type": "NetworkPing"}
        )


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When create() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseError(message="boom", status_code=500)

        mgr = MonitTestManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(state="present", params={"name": "X"})

        assert any("create failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_name_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'name' raises FieldValidationError before API call."""
        mgr = MonitTestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"type": "Custom"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_type_enum_raises(self, mock_client: AsyncMock) -> None:
        """Invalid 'type' enum raises FieldValidationError before API call."""
        mgr = MonitTestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "X", "type": "NotAType"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_action_enum_raises(self, mock_client: AsyncMock) -> None:
        """Invalid 'action' enum raises FieldValidationError before API call."""
        mgr = MonitTestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "X", "action": "reboot"})
        mock_client.create.assert_not_awaited()
