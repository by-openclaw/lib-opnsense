"""Unit tests for opnsense.managers.ub_forward.UbForwardManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError, FieldValidationError, OpnsenseValidationError
from opnsense.managers.ub_forward import UbForwardManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_forward(self, mock_client: AsyncMock) -> None:
        """ensure present when forward does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "domain": "example.com",
                "server": "10.0.0.53",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when forward matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "domain": "example.com",
                "server": "10.0.0.53",
                "type": "forward",
            },
        ]

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "domain": "example.com",
                "server": "10.0.0.53",
                "type": "forward",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when type differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "domain": "example.com",
                "server": "10.0.0.53",
                "type": "forward",
            },
        ]
        mock_client.get.return_value = {
            "dot": {
                "uuid": "uuid-existing",
                "domain": "example.com",
                "server": "10.0.0.53",
                "type": "forward",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "domain": "example.com",
                "server": "10.0.0.53",
                "type": "stub",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_forward(self, mock_client: AsyncMock) -> None:
        """ensure absent when forward exists -> delete + apply."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "domain": "example.com", "server": "10.0.0.53"},
        ]
        mock_client.get.return_value = {
            "dot": {"uuid": "uuid-existing", "domain": "example.com", "server": "10.0.0.53"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"domain": "example.com", "server": "10.0.0.53"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("unbound/service/reconfigure", timeout=60)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when forward does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"domain": "nonexistent"},
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"domain": "example.com", "server": "10.0.0.53"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
        ]
        mock_client.get.return_value = {
            "dot": {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
        }

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"domain": "example.com", "server": "10.0.0.53"},
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
            message="invalid forward", endpoint="unbound/settings/addForward"
        )

        mgr = UbForwardManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={"domain": "bad.example.com", "server": "10.0.0.53"},
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
        ]
        mock_client.get.return_value = {
            "dot": {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="unbound/settings/delForward"
        )

        mgr = UbForwardManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="absent",
                params={"domain": "example.com", "server": "10.0.0.53"},
            )

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_domain_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = UbForwardManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"server": "10.0.0.53"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_type_enum_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        mgr = UbForwardManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"domain": "example.com", "server": "10.0.0.53", "type": "recursive"},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """Tests for AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        """Two forwards with same composite keys -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
            {"uuid": "uuid-2", "domain": "example.com", "server": "10.0.0.53"},
        ]

        mgr = UbForwardManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={"domain": "example.com", "server": "10.0.0.53", "type": "forward"},
            )

        assert len(exc_info.value.uuids) == 2
        assert "uuid-1" in exc_info.value.uuids
        assert "uuid-2" in exc_info.value.uuids

    async def test_ambiguous_match_on_delete(self, mock_client: AsyncMock) -> None:
        """Delete with ambiguous match -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
            {"uuid": "uuid-2", "domain": "example.com", "server": "10.0.0.53"},
        ]

        mgr = UbForwardManager(mock_client)
        with pytest.raises(AmbiguousMatchError):
            await mgr.ensure(
                state="absent",
                params={"domain": "example.com", "server": "10.0.0.53"},
            )

    async def test_no_ambiguity_different_composite_key(self, mock_client: AsyncMock) -> None:
        """Two forwards with same domain but different server -> no ambiguity."""
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "domain": "example.com", "server": "10.0.0.53"},
            {"uuid": "uuid-2", "domain": "example.com", "server": "10.0.0.54"},
        ]

        mgr = UbForwardManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"domain": "example.com", "server": "10.0.0.53", "type": "forward"},
        )
        assert result.action == "noop"
