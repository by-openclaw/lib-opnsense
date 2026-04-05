"""Unit tests for opnsense.managers.ub_forward.UbForwardManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.ub_forward import UbForwardManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure("present", {"domain": "example.com"})

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure")

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "domain": "example.com"},
        ]

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure("present", {"domain": "example.com"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", "domain": "example.com"}]
        mock_client.get.return_value = {"dot": {"uuid": "uuid-1", "domain": "example.com"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure("absent", {"domain": "example.com"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure("absent", {"domain": "example.com"})

        assert result.changed is False


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(message="invalid", endpoint="test")

        mgr = UbForwardManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure("present", {"domain": "example.com"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = UbForwardManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure("running", {"domain": "example.com"})
