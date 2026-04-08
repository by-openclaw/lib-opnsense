"""Unit tests for opnsense.managers.kea6_subnet.Kea6SubnetManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.kea6_subnet import Kea6SubnetManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_subnet(self, mock_client: AsyncMock) -> None:
        """ensure present when subnet does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "subnet": "2001:db8::/64",
                "interface": "lan",
                "description": "IPv6 LAN pool",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when subnet matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "subnet": "2001:db8::/64",
                "interface": "lan",
                "description": "IPv6 LAN pool",
            },
        ]

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "subnet": "2001:db8::/64",
                "interface": "lan",
                "description": "IPv6 LAN pool",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when description differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "subnet": "2001:db8::/64",
                "interface": "lan",
                "description": "old description",
            },
        ]
        mock_client.get.return_value = {
            "subnet6": {
                "uuid": "uuid-existing",
                "subnet": "2001:db8::/64",
                "interface": "lan",
                "description": "old description",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "subnet": "2001:db8::/64",
                "interface": "lan",
                "description": "new description",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_subnet(self, mock_client: AsyncMock) -> None:
        """ensure absent when subnet exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "subnet": "2001:db8::/64", "interface": "lan"},
        ]
        mock_client.get.return_value = {
            "subnet6": {"uuid": "uuid-existing", "subnet": "2001:db8::/64", "interface": "lan"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="absent", params={"subnet": "2001:db8::/64", "interface": "lan"}
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when subnet does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="absent", params={"subnet": "2001:db8::/64", "interface": "lan"}
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"subnet": "2001:db8::/64", "interface": "lan"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "subnet": "2001:db8::/64", "interface": "lan"},
        ]
        mock_client.get.return_value = {
            "subnet6": {"uuid": "uuid-1", "subnet": "2001:db8::/64", "interface": "lan"},
        }

        mgr = Kea6SubnetManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"subnet": "2001:db8::/64", "interface": "lan"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally -- errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid subnet", endpoint="kea/dhcpv6/addSubnet"
        )

        mgr = Kea6SubnetManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"subnet": "bad", "interface": "lan"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "subnet": "2001:db8::/64", "interface": "lan"},
        ]
        mock_client.get.return_value = {
            "subnet6": {"uuid": "uuid-1", "subnet": "2001:db8::/64", "interface": "lan"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="kea/dhcpv6/delSubnet"
        )

        mgr = Kea6SubnetManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"subnet": "2001:db8::/64", "interface": "lan"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_subnet_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = Kea6SubnetManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"description": "test"})
        mock_client.create.assert_not_awaited()

    async def test_subnet_too_long_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = Kea6SubnetManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"subnet": "x" * 256})
        mock_client.create.assert_not_awaited()
