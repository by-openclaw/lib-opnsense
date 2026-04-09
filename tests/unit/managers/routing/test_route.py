"""Unit tests for opnsense.managers.rt_route.RtRouteManager.

Tests cover all BaseManager endpoints:
    - ensure(present): create, noop (no drift), update (drift)
    - ensure(absent): delete, noop (already absent)
    - check_mode: create, delete, noop
    - error handling: create failure logs + re-raises, invalid state, type preserved
    - field validation: required fields
    - ambiguous match: composite key collision
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseError,
    OpnsenseValidationError,
)
from opnsense.managers.routing.route import RtRouteManager

# Standard test params matching real OPNsense route config
ROUTE_PARAMS = {
    "network": "10.99.0.0/24",
    "gateway": "WAN_DHCP",
    "descr": "inttest-route",
    "disabled": "1",
}


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_route(self, mock_client: AsyncMock) -> None:
        """ensure present when route does not exist -> create + reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(state="present", params=ROUTE_PARAMS)

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once_with("routes/routes/addRoute", "route", ROUTE_PARAMS)
        mock_client.reconfigure.assert_awaited_once_with("routes/routes/reconfigure", timeout=None)

    async def test_noop_when_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when route exists with matching params -> noop."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", **ROUTE_PARAMS},
        ]

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(state="present", params=ROUTE_PARAMS)

        assert result.changed is False
        assert result.action == "noop"
        assert result.uuid == "uuid-1"
        mock_client.create.assert_not_awaited()
        mock_client.update.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when route descr changed -> update + reconfigure."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", **ROUTE_PARAMS},
        ]
        mock_client.get.return_value = {
            "route": {"uuid": "uuid-1", **ROUTE_PARAMS},
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "network": "10.99.0.0/24",
                "gateway": "WAN_DHCP",
                "descr": "inttest-route-updated",
                "disabled": "1",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        assert result.uuid == "uuid-1"
        mock_client.update.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("routes/routes/reconfigure", timeout=None)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_route(self, mock_client: AsyncMock) -> None:
        """ensure absent when route exists -> delete + reconfigure."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **ROUTE_PARAMS}]
        mock_client.get.return_value = {
            "route": {"uuid": "uuid-1", **ROUTE_PARAMS},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"network": "10.99.0.0/24", "gateway": "WAN_DHCP"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        assert result.uuid == "uuid-1"
        mock_client.delete.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when route does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"network": "10.99.99.0/24", "gateway": "WAN_DHCP"},
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode create -> changed=True but no create/reconfigure API call."""
        mock_client.search.return_value = []

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(state="present", params=ROUTE_PARAMS, check_mode=True)

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        """check_mode delete -> changed=True but no delete API call."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **ROUTE_PARAMS}]
        mock_client.get.return_value = {
            "route": {"uuid": "uuid-1", **ROUTE_PARAMS},
        }

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"network": "10.99.0.0/24", "gateway": "WAN_DHCP"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_noop_stays_noop(self, mock_client: AsyncMock) -> None:
        """check_mode on already matching state -> noop."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **ROUTE_PARAMS}]

        mgr = RtRouteManager(mock_client)
        result = await mgr.ensure(state="present", params=ROUTE_PARAMS, check_mode=True)

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
            message="network required",
            endpoint="routes/routes/addRoute",
        )

        mgr = RtRouteManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params=ROUTE_PARAMS)

        assert any("create failed" in r.message for r in caplog.records)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When delete() fails, manager logs ERROR and re-raises."""
        mock_client.search.return_value = [{"uuid": "uuid-1", **ROUTE_PARAMS}]
        mock_client.get.return_value = {
            "route": {"uuid": "uuid-1", **ROUTE_PARAMS},
        }
        mock_client.delete.side_effect = OpnsenseError(message="server error", status_code=500)

        mgr = RtRouteManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseError),
        ):
            await mgr.ensure(
                state="absent",
                params={"network": "10.99.0.0/24", "gateway": "WAN_DHCP"},
            )

        assert any("delete failed" in r.message for r in caplog.records)

    async def test_invalid_state_raises_value_error(self, mock_client: AsyncMock) -> None:
        """Invalid state raises ValueError immediately."""
        mgr = RtRouteManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"network": "10.0.0.0/8"})

    async def test_error_preserves_exception_type(self, mock_client: AsyncMock) -> None:
        """Re-raised exception keeps its original type (not wrapped)."""
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="bad input",
            endpoint="routes/routes/addRoute",
            validations={"route.network": "required"},
        )

        mgr = RtRouteManager(mock_client)
        with pytest.raises(OpnsenseValidationError) as exc_info:
            await mgr.ensure(state="present", params=ROUTE_PARAMS)

        assert exc_info.value.status_code == 400
        assert exc_info.value.validations == {"route.network": "required"}


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_network_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'network' raises FieldValidationError."""
        mgr = RtRouteManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"gateway": "WAN_DHCP", "descr": "test"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_gateway_raises(self, mock_client: AsyncMock) -> None:
        """Missing required 'gateway' raises FieldValidationError."""
        mgr = RtRouteManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"network": "10.99.0.0/24", "descr": "test"})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "aaa",
                "network": "10.99.0.0/24",
                "gateway": "WAN_DHCP",
                "descr": "route-1",
            },
            {
                "uuid": "bbb",
                "network": "10.99.0.0/24",
                "gateway": "WAN_DHCP",
                "descr": "route-2",
            },
        ]
        mgr = RtRouteManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                "present",
                params={
                    "network": "10.99.0.0/24",
                    "gateway": "WAN_DHCP",
                    "descr": "route-1",
                },
            )
        assert exc_info.value.uuids == ["aaa", "bbb"]
        mock_client.create.assert_not_awaited()
