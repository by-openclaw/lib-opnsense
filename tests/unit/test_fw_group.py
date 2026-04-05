"""Unit tests for opnsense.managers.fw_group.FwGroupManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import OpnsenseValidationError
from opnsense.managers.fw_group import FwGroupManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create_new_group(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = FwGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": "trusted", "members": "lan,wireguard", "descr": "Trusted"},
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_not_awaited()

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "ifname": "trusted", "members": "lan,wireguard"},
        ]

        mgr = FwGroupManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"ifname": "trusted", "members": "lan,wireguard"},
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "uuid-1", "ifname": "trusted"}]
        mock_client.get.return_value = {"group": {"uuid": "uuid-1", "ifname": "trusted"}}
        mock_client.delete.return_value = {"result": "deleted"}

        mgr = FwGroupManager(mock_client)
        result = await mgr.ensure(state="absent", params={"ifname": "trusted"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwGroupManager(mock_client)
        result = await mgr.ensure(state="absent", params={"ifname": "nonexistent"})

        assert result.changed is False


@pytest.mark.asyncio
class TestMatchKey:
    async def test_match_key_is_ifname(self) -> None:
        assert FwGroupManager._match_key == "ifname"

    async def test_no_apply_endpoint(self) -> None:
        assert FwGroupManager._apply_endpoint is None


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid", endpoint="firewall/group/addItem"
        )

        mgr = FwGroupManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"ifname": "bad"})

        assert any("create failed" in r.message for r in caplog.records)
