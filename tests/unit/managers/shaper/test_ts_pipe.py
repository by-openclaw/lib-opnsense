"""Unit tests for opnsense.managers.ts_pipe.TsPipeManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError, FieldValidationError, OpnsenseValidationError
from opnsense.managers.shaper.ts_pipe import TsPipeManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create_new_pipe(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
                "enabled": "1",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_awaited_once_with(
            "trafficshaper/service/reconfigure", timeout=None
        )

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Upload limit",
                "bandwidth": "100",
            },
        ]

        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Upload limit", "bandwidth": "100"},
        )

        assert result.changed is False
        assert result.action == "noop"

    async def test_update(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
                "enabled": "1",
            },
        ]
        mock_client.get.return_value = {
            "pipe": {
                "uuid": "uuid-1",
                "description": "Upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
                "enabled": "1",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
                "enabled": "0",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "Upload limit"},
        ]
        mock_client.get.return_value = {
            "pipe": {"uuid": "uuid-1", "description": "Upload limit"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "Upload limit"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False


@pytest.mark.asyncio
class TestSearchOverride:
    async def test_list_uses_search_pipes(self, mock_client: AsyncMock) -> None:
        """list() uses search_pipes (plural) not searchPipe."""
        mock_client.search.return_value = []
        mgr = TsPipeManager(mock_client)
        await mgr.list()
        mock_client.search.assert_awaited_once_with(
            "trafficshaper/settings/search_pipes", search_phrase=""
        )

    async def test_create_uses_add_pipe(self, mock_client: AsyncMock) -> None:
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsPipeManager(mock_client)
        await mgr.create(params={"description": "test", "bandwidth": "10"})

        mock_client.create.assert_awaited_once_with(
            "trafficshaper/settings/addPipe",
            "pipe",
            {"description": "test", "bandwidth": "10"},
        )


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid", endpoint="trafficshaper/settings/addPipe"
        )

        mgr = TsPipeManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"description": "bad", "bandwidth": "10"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = TsPipeManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"description": "x"})


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_empty_description_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """Empty required 'description' raises FieldValidationError."""
        mgr = TsPipeManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"description": "", "bandwidth": "100"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = TsPipeManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"bandwidth": "100"})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(
            "present",
            params={"description": "Upload limit", "bandwidth": "100"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()

    async def test_check_mode_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
            },
        ]
        mock_client.get.return_value = {
            "pipe": {
                "uuid": "uuid-1",
                "description": "Upload limit",
                "bandwidth": "100",
                "bandwidthMetric": "Mbit",
            },
        }
        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(
            "absent",
            params={"description": "Upload limit", "bandwidth": "100", "bandwidthMetric": "Mbit"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        pipe_data = {
            "description": "Upload limit",
            "bandwidth": "100",
            "bandwidthMetric": "Mbit",
        }
        mock_client.search.return_value = [
            {"uuid": "aaa", **pipe_data},
            {"uuid": "bbb", **pipe_data},
        ]
        mgr = TsPipeManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure("present", params=pipe_data)
        assert exc_info.value.uuids == ["aaa", "bbb"]
        mock_client.create.assert_not_awaited()
