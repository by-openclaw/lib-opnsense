"""Unit tests for opnsense.managers.rt_gateway.RtGatewayManager.

Tests cover all BaseManager endpoints:
    - ensure(present): create, noop (no drift), update (drift)
    - ensure(absent): delete, noop (already absent)
    - check_mode: create, delete, noop
    - error handling: create failure logs + re-raises, invalid state, type preserved
    - field validation: required fields, enum, range
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    FieldValidationError,
    OpnsenseError,
    OpnsenseValidationError,
)
from opnsense.managers.rt_gateway import RtGatewayManager

# Standard test params matching real OPNsense gateway config
GW_PARAMS = {"name": "WAN_GW", "interface": "wan", "gateway": "10.0.0.1"}


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_gateway(self, mock_client: AsyncMock) -> None:
        """ensure present when gateway does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="present", params=GW_PARAMS)

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once_with(
            "routing/settings/addGateway", "gateway_item", GW_PARAMS
        )
        mock_client.reconfigure.assert_awaited_once_with(
            "routing/settings/reconfigure", timeout=None
        )

    async def test_noop_when_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when gateway exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", **GW_PARAMS},
        ]

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="present", params=GW_PARAMS)

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-1"
        mock_client.create.assert_not_awaited()
        mock_client.update.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when gateway changed -> update + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", **GW_PARAMS},
        ]
        mock_client.get.return_value = {
            "gateway_item": {"uuid": "uuid-1", **GW_PARAMS},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "WAN_GW", "interface": "wan", "gateway": "10.0.0.2"},
        )

        assert result.changed is True
        assert result.action == "updated"
        assert result.uuid == "uuid-1"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "routing/settings/reconfigure", timeout=None
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_gateway(self, mock_client: AsyncMock) -> None:
        """ensure absent when gateway exists -> delete + reconfigure."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **GW_PARAMS}]
        mock_client.get.return_value = {
            "gateway_item": {"uuid": "uuid-1", **GW_PARAMS},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "WAN_GW"})

        assert result.changed is True
        assert result.action == "deleted"
        assert result.uuid == "uuid-1"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when gateway does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no create/reconfigure API call."""
        mock_client.search.return_value = []

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="present", params=GW_PARAMS, check_mode=True)

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode delete -> changed=True but no delete API call."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **GW_PARAMS}]
        mock_client.get.return_value = {
            "gateway_item": {"uuid": "uuid-1", **GW_PARAMS},
        }

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "WAN_GW"}, check_mode=True)

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_noop_stays_noop(self, mock_client: AsyncMock) -> None:
        """check_mode on already matching state -> noop."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **GW_PARAMS}]

        mgr = RtGatewayManager(mock_client)
        result = await mgr.ensure(state="present", params=GW_PARAMS, check_mode=True)

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally -- errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When create() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="name required",
            endpoint="routing/settings/addGateway",
        )

        mgr = RtGatewayManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params=GW_PARAMS)

        assert any("create failed" in r.message for r in caplog.records)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When delete() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **GW_PARAMS}]
        mock_client.get.return_value = {
            "gateway_item": {"uuid": "uuid-1", **GW_PARAMS},
        }
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = RtGatewayManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(state="absent", params={"name": "WAN_GW"})

        assert any("delete failed" in r.message for r in caplog.records)

    async def test_invalid_state_raises_value_error(self, mock_client: AsyncMock) -> None:
        """Invalid state raises ValueError immediately."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"name": "WAN_GW"})

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        """Re-raised exception keeps its original type (not wrapped)."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="routing/settings/addGateway",
            validations={"gateway_item.name": "required"},
        )

        mgr = RtGatewayManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params=GW_PARAMS)

        assert exc_info.value.status_code == 400
        assert exc_info.value.validations == {"gateway_item.name": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_name_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'name' raises FieldValidationError."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"interface": "wan", "gateway": "10.0.0.1"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_interface_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'interface' raises FieldValidationError."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "WAN_GW", "gateway": "10.0.0.1"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_gateway_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'gateway' raises FieldValidationError."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "WAN_GW", "interface": "wan"})
        mock_client.create.assert_not_awaited()

    async def test_priority_out_of_range_raises(self, mock_client: AsyncMock) -> None:
        """priority=999 exceeds max 255, raises FieldValidationError."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={**GW_PARAMS, "priority": "999"})
        mock_client.create.assert_not_awaited()

    async def test_weight_out_of_range_raises(self, mock_client: AsyncMock) -> None:
        """weight=10 exceeds max 5, raises FieldValidationError."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={**GW_PARAMS, "weight": "10"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_ipprotocol_raises(self, mock_client: AsyncMock) -> None:
        """Invalid ipprotocol enum raises FieldValidationError."""
        mgr = RtGatewayManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={**GW_PARAMS, "ipprotocol": "inet7"})
        mock_client.create.assert_not_awaited()
