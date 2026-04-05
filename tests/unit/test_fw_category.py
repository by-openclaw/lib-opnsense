"""Unit tests for opnsense.managers.fw_category.FwCategoryManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.fw_category import FwCategoryManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create_new_category(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = FwCategoryManager(mock_client)
        result = await mgr.ensure(state="present", params={"name": "infra", "color": "0000ff"})

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_not_awaited()  # no reconfigure

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "infra", "color": "0000ff"},
        ]

        mgr = FwCategoryManager(mock_client)
        result = await mgr.ensure(state="present", params={"name": "infra", "color": "0000ff"})

        assert result.changed is False
        assert result.action == "noop"

    async def test_update(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "infra", "color": "0000ff"},
        ]
        mock_client.get.return_value = {
            "category": {"uuid": "uuid-1", "name": "infra", "color": "0000ff"},
        }
        mock_client.update.return_value = {"result": "saved"}

        mgr = FwCategoryManager(mock_client)
        result = await mgr.ensure(state="present", params={"name": "infra", "color": "ff0000"})

        assert result.changed is True
        assert result.action == "updated"


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", "name": "infra"}]
        mock_client.get.return_value = {"category": {"uuid": "uuid-1", "name": "infra"}}
        mock_client.delete.return_value = {"result": "deleted"}

        mgr = FwCategoryManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "infra"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwCategoryManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "nonexistent"})

        assert result.changed is False


@pytest.mark.asyncio
class TestEndpointSuffix:
    async def test_search_uses_item(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = FwCategoryManager(mock_client)
        await mgr.list()
        mock_client.search.assert_awaited_once_with(
            "firewall/category/searchItem", search_phrase=""
        )

    async def test_no_apply_endpoint(self) -> None:
        assert FwCategoryManager._apply_endpoint is None


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid color", endpoint="firewall/category/addItem"
        )

        mgr = FwCategoryManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"name": "bad"})

        assert any("create failed" in r.message for r in caplog.records)
