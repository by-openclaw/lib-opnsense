"""Unit tests for opnsense.managers.ovpn_instance.OvpnInstanceManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.vpn.ovpn_instance import OvpnInstanceManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_instance(self, mock_client: AsyncMock) -> None:
        """ensure present when instance does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "office-vpn",
                "role": "server",
                "proto": "udp",
                "port": "1194",
                "server": "10.8.0.0/24",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("openvpn/service/reconfigure", timeout=30)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when instance matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
                "server": "10.8.0.0/24",
            },
        ]

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
                "server": "10.8.0.0/24",
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
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
                "server": "10.8.0.0/24",
            },
        ]
        mock_client.get.return_value = {
            "instance": {
                "uuid": "uuid-existing",
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
                "server": "10.8.0.0/24",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "office-vpn",
                "role": "server",
                "port": "1195",
                "server": "10.8.0.0/24",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("openvpn/service/reconfigure", timeout=30)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_instance(self, mock_client: AsyncMock) -> None:
        """ensure absent when instance exists -> delete + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
            },
        ]
        mock_client.get.return_value = {
            "instance": {
                "uuid": "uuid-existing",
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "office-vpn"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("openvpn/service/reconfigure", timeout=30)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when instance does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "nonexistent"},
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
                "server": "10.8.0.0/24",
            },
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
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
            },
        ]
        mock_client.get.return_value = {
            "instance": {
                "uuid": "uuid-1",
                "description": "office-vpn",
                "role": "server",
                "port": "1194",
            },
        }

        mgr = OvpnInstanceManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "office-vpn"},
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
            message="invalid instance", endpoint="openvpn/instances/add"
        )

        mgr = OvpnInstanceManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={"description": "bad"},
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "office-vpn",
            },
        ]
        mock_client.get.return_value = {
            "instance": {
                "uuid": "uuid-1",
                "description": "office-vpn",
            },
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="openvpn/instances/del"
        )

        mgr = OvpnInstanceManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="absent",
                params={"description": "office-vpn"},
            )

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = OvpnInstanceManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"port": "1194"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_port_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = OvpnInstanceManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "office-vpn", "port": "99999"},
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_role_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = OvpnInstanceManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "office-vpn", "role": "invalid"},
            )
        mock_client.create.assert_not_awaited()

    async def test_description_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = OvpnInstanceManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "x" * 256},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on OvpnInstanceManager."""

    async def test_redact_fields_defined(self) -> None:
        """OvpnInstanceManager redacts password and auth-gen-token-secret."""
        assert "password" in OvpnInstanceManager.REDACT_FIELDS
        assert "auth-gen-token-secret" in OvpnInstanceManager.REDACT_FIELDS
        assert len(OvpnInstanceManager.REDACT_FIELDS) == 2
