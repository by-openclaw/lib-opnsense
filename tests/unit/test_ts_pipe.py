"""Unit tests for opnsense.managers.ts_pipe.TsPipeManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.ts_pipe import TsPipeManager


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
        mock_client.reconfigure.assert_awaited_once_with("trafficshaper/service/reconfigure")

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
            {"uuid": "uuid-1", "description": "Upload limit", "bandwidth": "100"},
        ]
        mock_client.get.return_value = {
            "pipe": {"uuid": "uuid-1", "description": "Upload limit", "bandwidth": "100"},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = TsPipeManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Upload limit", "bandwidth": "50"},
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
            await mgr.ensure(state="present", params={"description": "bad"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = TsPipeManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"description": "x"})
