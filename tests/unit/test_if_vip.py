"""Unit tests for opnsense.managers.if_vip.IfVipManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.if_vip import IfVipManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure("present", {"descr": "CARP VIP"})

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_awaited_once_with("interfaces/vip_settings/reconfigure")

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "descr": "CARP VIP"},
        ]

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure("present", {"descr": "CARP VIP"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", "descr": "CARP VIP"}]
        mock_client.get.return_value = {"vip": {"uuid": "uuid-1", "descr": "CARP VIP"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure("absent", {"descr": "CARP VIP"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IfVipManager(mock_client)
        result = await mgr.ensure("absent", {"descr": "CARP VIP"})

        assert result.changed is False


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(message="invalid", endpoint="test")

        mgr = IfVipManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure("present", {"descr": "CARP VIP"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = IfVipManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure("running", {"descr": "CARP VIP"})

    async def test_redact_fields(self) -> None:
        assert "password" in IfVipManager.REDACT_FIELDS
