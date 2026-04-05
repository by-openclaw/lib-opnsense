"""Unit tests for opnsense.managers.kea_subnet.KeaSubnetManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.kea_subnet import KeaSubnetManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = KeaSubnetManager(mock_client)
        result = await mgr.ensure("present", {"subnet": "10.1.3.0/24"})

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure")

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "subnet": "10.1.3.0/24"},
        ]

        mgr = KeaSubnetManager(mock_client)
        result = await mgr.ensure("present", {"subnet": "10.1.3.0/24"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", "subnet": "10.1.3.0/24"}]
        mock_client.get.return_value = {"subnet4": {"uuid": "uuid-1", "subnet": "10.1.3.0/24"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = KeaSubnetManager(mock_client)
        result = await mgr.ensure("absent", {"subnet": "10.1.3.0/24"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = KeaSubnetManager(mock_client)
        result = await mgr.ensure("absent", {"subnet": "10.1.3.0/24"})

        assert result.changed is False


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(message="invalid", endpoint="test")

        mgr = KeaSubnetManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure("present", {"subnet": "10.1.3.0/24"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = KeaSubnetManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure("running", {"subnet": "10.1.3.0/24"})
