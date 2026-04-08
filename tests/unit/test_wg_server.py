"""Unit tests for opnsense.managers.wg_server.WgServerManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.wg_server import WgServerManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_server(self, mock_client: AsyncMock) -> None:
        """ensure present when server does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "wg0",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "wireguard/service/reconfigure", timeout=30
        )

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when server matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "wg0",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
            },
        ]

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "wg0",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when port differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "wg0",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
            },
        ]
        mock_client.get.return_value = {
            "server": {
                "uuid": "uuid-existing",
                "name": "wg0",
                "port": "51820",
                "tunneladdress": "10.10.0.1/24",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "wg0",
                "port": "51821",
                "tunneladdress": "10.10.0.1/24",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with(
            "wireguard/service/reconfigure", timeout=30
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_server(self, mock_client: AsyncMock) -> None:
        """ensure absent when server exists -> delete + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "wg0",
                "port": "51820",
            },
        ]
        mock_client.get.return_value = {
            "server": {
                "uuid": "uuid-existing",
                "name": "wg0",
                "port": "51820",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "wg0"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with(
            "wireguard/service/reconfigure", timeout=30
        )

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when server does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "nonexistent"},
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "wg0", "port": "51820", "tunneladdress": "10.10.0.1/24"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "name": "wg0",
                "port": "51820",
            },
        ]
        mock_client.get.return_value = {
            "server": {
                "uuid": "uuid-1",
                "name": "wg0",
                "port": "51820",
            },
        }

        mgr = WgServerManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "wg0"},
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
            message="invalid server", endpoint="wireguard/server/addServer"
        )

        mgr = WgServerManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={"name": "bad"},
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "name": "wg0",
            },
        ]
        mock_client.get.return_value = {
            "server": {
                "uuid": "uuid-1",
                "name": "wg0",
            },
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="wireguard/server/delServer"
        )

        mgr = WgServerManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="absent",
                params={"name": "wg0"},
            )

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_name_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = WgServerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"port": "51820"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_port_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = WgServerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"name": "wg0", "port": "99999"},
            )
        mock_client.create.assert_not_awaited()

    async def test_mtu_below_min_raises(self, mock_client: AsyncMock) -> None:
        mgr = WgServerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"name": "wg0", "mtu": "10"},
            )
        mock_client.create.assert_not_awaited()

    async def test_mtu_above_max_raises(self, mock_client: AsyncMock) -> None:
        mgr = WgServerManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"name": "wg0", "mtu": "10000"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on WgServerManager."""

    async def test_redact_fields_defined(self) -> None:
        """WgServerManager redacts privkey and pubkey."""
        assert "privkey" in WgServerManager.REDACT_FIELDS
        assert "pubkey" in WgServerManager.REDACT_FIELDS
        assert len(WgServerManager.REDACT_FIELDS) == 2
