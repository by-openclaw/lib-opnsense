"""Unit tests for opnsense.managers.ts_queue.TsQueueManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.ts_queue import TsQueueManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_queue(self, mock_client: AsyncMock) -> None:
        """ensure present when queue does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsQueueManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "VoIP priority",
                "weight": "90",
                "enabled": "1",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when queue matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "VoIP priority",
                "weight": "90",
                "enabled": "1",
            },
        ]

        mgr = TsQueueManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "VoIP priority",
                "weight": "90",
                "enabled": "1",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when weight differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "VoIP priority",
                "weight": "50",
                "enabled": "1",
            },
        ]
        mock_client.get.return_value = {
            "queue": {
                "uuid": "uuid-existing",
                "description": "VoIP priority",
                "weight": "50",
                "enabled": "1",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsQueueManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "VoIP priority", "weight": "90"},
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_queue(self, mock_client: AsyncMock) -> None:
        """ensure absent when queue exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "VoIP priority"},
        ]
        mock_client.get.return_value = {
            "queue": {"uuid": "uuid-existing", "description": "VoIP priority"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsQueueManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "VoIP priority"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when queue does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = TsQueueManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = TsQueueManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Test queue", "weight": "50"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally — errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid queue", endpoint="trafficshaper/settings/addQueue"
        )

        mgr = TsQueueManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"description": "bad", "weight": "50"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="trafficshaper/settings/addQueue",
            validations={"queue.weight": "required"},
        )

        mgr = TsQueueManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params={"description": "bad", "weight": "50"})

        assert exc_info.value.validations == {"queue.weight": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_invalid_mask_enum_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """mask='bad-value' fails enum validation."""
        mgr = TsQueueManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "test", "mask": "bad-value"},
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = TsQueueManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"weight": "50"})
        mock_client.create.assert_not_awaited()

    async def test_weight_below_min_raises(self, mock_client: AsyncMock) -> None:
        """weight=0 fails min validation."""
        mgr = TsQueueManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "test", "weight": "0"},
            )
        mock_client.create.assert_not_awaited()

    async def test_weight_above_max_raises(self, mock_client: AsyncMock) -> None:
        """weight=101 fails max validation."""
        mgr = TsQueueManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "test", "weight": "101"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestSearchOverride:
    """Verify list() uses the plural searchQueues endpoint."""

    async def test_list_uses_search_queues_plural(self, mock_client: AsyncMock) -> None:
        """list() must call trafficshaper/settings/searchQueues (plural)."""
        mock_client.search.return_value = []

        mgr = TsQueueManager(mock_client)
        await mgr.list()

        mock_client.search.assert_awaited_once_with(
            "trafficshaper/settings/searchQueues", search_phrase=""
        )

    async def test_list_passes_search_phrase(self, mock_client: AsyncMock) -> None:
        """list(search_phrase=) is forwarded to the client."""
        mock_client.search.return_value = []

        mgr = TsQueueManager(mock_client)
        await mgr.list(search_phrase="voip")

        mock_client.search.assert_awaited_once_with(
            "trafficshaper/settings/searchQueues", search_phrase="voip"
        )
