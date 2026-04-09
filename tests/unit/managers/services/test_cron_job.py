# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.cron_job.CronJobManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.services.cron_job import CronJobManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_job(self, mock_client: AsyncMock) -> None:
        """ensure present when job does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Update bogons nightly",
                "enabled": "1",
                "minutes": "0",
                "hours": "3",
                "days": "*",
                "months": "*",
                "weekdays": "*",
                "command": "filter update bogons",
                "who": "root",
                "parameters": "",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("cron/service/reconfigure", timeout=15)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when job matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Update bogons nightly",
                "enabled": "1",
                "minutes": "0",
                "hours": "3",
                "command": "filter update bogons",
            },
        ]

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Update bogons nightly",
                "enabled": "1",
                "minutes": "0",
                "hours": "3",
                "command": "filter update bogons",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when hours differ -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Update bogons nightly",
                "hours": "3",
            },
        ]
        mock_client.get.return_value = {
            "job": {
                "uuid": "uuid-existing",
                "description": "Update bogons nightly",
                "hours": "3",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Update bogons nightly",
                "hours": "5",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("cron/service/reconfigure", timeout=15)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_job(self, mock_client: AsyncMock) -> None:
        """ensure absent when job exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "Update bogons nightly"},
        ]
        mock_client.get.return_value = {
            "job": {"uuid": "uuid-existing", "description": "Update bogons nightly"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "Update bogons nightly"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("cron/service/reconfigure", timeout=15)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when job does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Test job", "enabled": "1"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "Test job"},
        ]
        mock_client.get.return_value = {
            "job": {"uuid": "uuid-1", "description": "Test job"},
        }

        mgr = CronJobManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "Test job"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid job", endpoint="cron/settings/addJob"
        )

        mgr = CronJobManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"description": "bad"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "Test job"},
        ]
        mock_client.get.return_value = {
            "job": {"uuid": "uuid-1", "description": "Test job"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="cron/settings/delJob"
        )

        mgr = CronJobManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"description": "Test job"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = CronJobManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"enabled": "1"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_enabled_bool_str_raises(self, mock_client: AsyncMock) -> None:
        mgr = CronJobManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "Test", "enabled": "yes"},
            )
        mock_client.create.assert_not_awaited()

    async def test_description_exceeds_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = CronJobManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "x" * 256},
            )
        mock_client.create.assert_not_awaited()
