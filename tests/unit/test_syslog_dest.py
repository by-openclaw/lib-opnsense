"""Unit tests for opnsense.managers.syslog_dest.SyslogDestManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.syslog_dest import SyslogDestManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create_new_destination(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Central syslog",
                "hostname": "syslog.example.com",
                "port": "514",
                "transport": "udp4",
                "enabled": "1",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_awaited_once_with("syslog/service/reconfigure", timeout=30)

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Central syslog",
                "hostname": "syslog.example.com",
            },
        ]

        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "Central syslog", "hostname": "syslog.example.com"},
        )

        assert result.changed is False
        assert result.action == "noop"

    async def test_update(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Central syslog",
                "hostname": "syslog.example.com",
                "port": "514",
                "transport": "udp4",
                "enabled": "1",
            },
        ]
        mock_client.get.return_value = {
            "destination": {
                "uuid": "uuid-1",
                "description": "Central syslog",
                "hostname": "syslog.example.com",
                "port": "514",
                "transport": "udp4",
                "enabled": "1",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Central syslog",
                "hostname": "syslog.example.com",
                "port": "514",
                "transport": "udp4",
                "enabled": "0",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once()


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "Central syslog"},
        ]
        mock_client.get.return_value = {
            "destination": {"uuid": "uuid-1", "description": "Central syslog"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "Central syslog"})

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(
            "present",
            params={
                "description": "Central syslog",
                "hostname": "syslog.example.com",
            },
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()

    async def test_check_mode_delete(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Central syslog",
                "hostname": "syslog.example.com",
            },
        ]
        mock_client.get.return_value = {
            "destination": {
                "uuid": "uuid-1",
                "description": "Central syslog",
                "hostname": "syslog.example.com",
            },
        }
        mgr = SyslogDestManager(mock_client)
        result = await mgr.ensure(
            "absent",
            params={"description": "Central syslog"},
            check_mode=True,
        )
        assert result.changed is True
        assert result.action == "deleted"
        mock_client.delete.assert_not_awaited()


@pytest.mark.asyncio
class TestErrorHandling:
    async def test_create_failure_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = []
        mock_client.create.side_effect = OpnsenseValidationError(
            message="invalid", endpoint="syslog/settings/addDestination"
        )

        mgr = SyslogDestManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "description": "bad",
                    "hostname": "syslog.example.com",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = SyslogDestManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"description": "x"})


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_empty_description_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """Empty required 'description' raises FieldValidationError."""
        mgr = SyslogDestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "", "hostname": "syslog.example.com"},
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = SyslogDestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"hostname": "syslog.example.com"})
        mock_client.create.assert_not_awaited()

    async def test_missing_required_hostname_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'hostname' raises FieldValidationError."""
        mgr = SyslogDestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"description": "Central syslog"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_transport_enum(self, mock_client: AsyncMock) -> None:
        """Invalid transport value raises FieldValidationError."""
        mgr = SyslogDestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "hostname": "syslog.example.com",
                    "transport": "sctp",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_enabled_bool_str(self, mock_client: AsyncMock) -> None:
        """Invalid enabled value raises FieldValidationError."""
        mgr = SyslogDestManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "hostname": "syslog.example.com",
                    "enabled": "yes",
                },
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestSearchOverride:
    async def test_list_uses_search_destinations_plural(self, mock_client: AsyncMock) -> None:
        """list() uses searchDestinations (plural) not searchDestination."""
        mock_client.search.return_value = []
        mgr = SyslogDestManager(mock_client)
        await mgr.list()
        mock_client.search.assert_awaited_once_with(
            "syslog/settings/searchDestinations", search_phrase=""
        )

    async def test_create_uses_add_destination(self, mock_client: AsyncMock) -> None:
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = SyslogDestManager(mock_client)
        await mgr.create(
            params={
                "description": "test",
                "hostname": "syslog.example.com",
            }
        )

        mock_client.create.assert_awaited_once_with(
            "syslog/settings/addDestination",
            "destination",
            {"description": "test", "hostname": "syslog.example.com"},
        )
