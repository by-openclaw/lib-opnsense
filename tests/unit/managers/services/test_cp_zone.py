"""Unit tests for opnsense.managers.cp_zone.CpZoneManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.services.cp_zone import CpZoneManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_zone(self, mock_client: AsyncMock) -> None:
        """ensure present when zone does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Guest WiFi",
                "enabled": "1",
                "interfaces": "opt1",
                "idletimeout": "300",
                "hardtimeout": "3600",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with(
            "captiveportal/service/reconfigure", timeout=30
        )

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when zone matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Guest WiFi",
                "enabled": "1",
                "interfaces": "opt1",
            },
        ]

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Guest WiFi",
                "enabled": "1",
                "interfaces": "opt1",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when idletimeout differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "Guest WiFi",
                "idletimeout": "300",
            },
        ]
        mock_client.get.return_value = {
            "zone": {
                "uuid": "uuid-existing",
                "description": "Guest WiFi",
                "idletimeout": "300",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Guest WiFi",
                "idletimeout": "600",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with(
            "captiveportal/service/reconfigure", timeout=30
        )


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_zone(self, mock_client: AsyncMock) -> None:
        """ensure absent when zone exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "Guest WiFi"},
        ]
        mock_client.get.return_value = {
            "zone": {"uuid": "uuid-existing", "description": "Guest WiFi"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "Guest WiFi"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with(
            "captiveportal/service/reconfigure", timeout=30
        )

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when zone does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Guest WiFi", "enabled": "1"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "Guest WiFi"},
        ]
        mock_client.get.return_value = {
            "zone": {"uuid": "uuid-1", "description": "Guest WiFi"},
        }

        mgr = CpZoneManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "Guest WiFi"},
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
            message="invalid zone", endpoint="captiveportal/settings/addZone"
        )

        mgr = CpZoneManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"description": "bad"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "Guest WiFi"},
        ]
        mock_client.get.return_value = {
            "zone": {"uuid": "uuid-1", "description": "Guest WiFi"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="captiveportal/settings/delZone"
        )

        mgr = CpZoneManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"description": "Guest WiFi"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = CpZoneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"enabled": "1"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_enabled_bool_str_raises(self, mock_client: AsyncMock) -> None:
        mgr = CpZoneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "Test", "enabled": "yes"},
            )
        mock_client.create.assert_not_awaited()

    async def test_idletimeout_below_min_raises(self, mock_client: AsyncMock) -> None:
        mgr = CpZoneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "Test", "idletimeout": "-1"},
            )
        mock_client.create.assert_not_awaited()

    async def test_description_exceeds_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = CpZoneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "x" * 256},
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_concurrentlogins_bool_str_raises(self, mock_client: AsyncMock) -> None:
        mgr = CpZoneManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "Test", "concurrentlogins": "true"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestSearchOverride:
    """Tests for list() override — uses searchZones (plural)."""

    async def test_list_uses_search_zones_plural(self, mock_client: AsyncMock) -> None:
        """list() uses searchZones (plural) not searchZone."""
        mock_client.search.return_value = []
        mgr = CpZoneManager(mock_client)
        await mgr.list()
        mock_client.search.assert_awaited_once_with(
            "captiveportal/settings/searchZones", search_phrase=""
        )

    async def test_create_uses_add_zone(self, mock_client: AsyncMock) -> None:
        """create() uses addZone endpoint."""
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = CpZoneManager(mock_client)
        await mgr.create(params={"description": "test", "enabled": "1"})

        mock_client.create.assert_awaited_once_with(
            "captiveportal/settings/addZone",
            "zone",
            {"description": "test", "enabled": "1"},
        )
