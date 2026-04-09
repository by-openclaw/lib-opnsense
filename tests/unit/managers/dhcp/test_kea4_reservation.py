"""Unit tests for opnsense.managers.kea4_reservation.Kea4ReservationManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import (
    AmbiguousMatchError,
    FieldValidationError,
    OpnsenseValidationError,
)
from opnsense.managers.dhcp.kea4_reservation import Kea4ReservationManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_reservation(self, mock_client: AsyncMock) -> None:
        """ensure present when reservation does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "printer",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when reservation matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "printer",
            },
        ]

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "printer",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when hostname differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "old-printer",
            },
        ]
        mock_client.get.return_value = {
            "reservation": {
                "uuid": "uuid-existing",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "old-printer",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "new-printer",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_reservation(self, mock_client: AsyncMock) -> None:
        """ensure absent when reservation exists -> delete + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
        ]
        mock_client.get.return_value = {
            "reservation": {
                "uuid": "uuid-existing",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("kea/service/reconfigure", timeout=60)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when reservation does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for try/except/finally -- errors are logged then re-raised."""

    async def test_create_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid reservation", endpoint="kea/dhcpv4/addReservation"
        )

        mgr = Kea4ReservationManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "ip_address": "10.0.0.50",
                    "hw_address": "00:11:22:33:44:55",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_ip_address_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4ReservationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"hw_address": "00:11:22:33:44:55"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_hw_address_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4ReservationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"ip_address": "10.0.0.50"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_ip_address_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4ReservationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"ip_address": "not-an-ip", "hw_address": "00:11:22:33:44:55"},
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_mac_address_raises(self, mock_client: AsyncMock) -> None:
        mgr = Kea4ReservationManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"ip_address": "10.0.0.50", "hw_address": "not-a-mac"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """Tests for AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        """Two reservations with same composite keys -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "printer-a",
            },
            {
                "uuid": "uuid-2",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
                "hostname": "printer-b",
            },
        ]

        mgr = Kea4ReservationManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "ip_address": "10.0.0.50",
                    "hw_address": "00:11:22:33:44:55",
                    "hostname": "printer",
                },
            )

        assert len(exc_info.value.uuids) == 2
        assert "uuid-1" in exc_info.value.uuids
        assert "uuid-2" in exc_info.value.uuids

    async def test_no_ambiguity_different_composite_key(self, mock_client: AsyncMock) -> None:
        """Two reservations with same IP but different MAC -> no ambiguity."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
            {
                "uuid": "uuid-2",
                "ip_address": "10.0.0.50",
                "hw_address": "AA:BB:CC:DD:EE:FF",
            },
        ]

        mgr = Kea4ReservationManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
        )
        assert result.action == "noop"

    async def test_ambiguous_match_on_delete(self, mock_client: AsyncMock) -> None:
        """Delete with ambiguous match -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
            {
                "uuid": "uuid-2",
                "ip_address": "10.0.0.50",
                "hw_address": "00:11:22:33:44:55",
            },
        ]

        mgr = Kea4ReservationManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={
                    "ip_address": "10.0.0.50",
                    "hw_address": "00:11:22:33:44:55",
                },
            )
