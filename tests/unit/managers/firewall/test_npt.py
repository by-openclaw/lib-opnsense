"""Unit tests for opnsense.managers.fw_npt.FwNptManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import AmbiguousMatchError, FieldValidationError, OpnsenseValidationError
from opnsense.managers.fw_npt import FwNptManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_rule(self, mock_client: AsyncMock) -> None:
        """ensure present when rule does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("firewall/npt/apply", timeout=None)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when rule matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
            },
        ]

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when interface differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "lan",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "lan",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("firewall/npt/apply", timeout=None)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_rule(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule exists -> delete + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("firewall/npt/apply", timeout=None)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when rule does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        )

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
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
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        }

        mgr = FwNptManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
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
            message="invalid rule", endpoint="firewall/npt/addRule"
        )

        mgr = FwNptManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "source_net": "fd00:1::/64",
                    "destination_net": "2001:db8:1::/64",
                    "interface": "wan",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        ]
        mock_client.get.return_value = {
            "rule": {
                "uuid": "uuid-existing",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
            },
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="firewall/npt/delRule/uuid-existing"
        )

        mgr = FwNptManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="absent",
                params={
                    "source_net": "fd00:1::/64",
                    "destination_net": "2001:db8:1::/64",
                },
            )

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_source_net_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """Missing required 'source_net' raises FieldValidationError."""
        mgr = FwNptManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "destination_net": "2001:db8:1::/64",
                    "interface": "wan",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_destination_net_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'destination_net' raises FieldValidationError."""
        mgr = FwNptManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "source_net": "fd00:1::/64",
                    "interface": "wan",
                },
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestAmbiguousMatch:
    """Tests for AmbiguousMatchError when multiple resources match composite keys."""

    async def test_ambiguous_match_raises(self, mock_client: AsyncMock) -> None:
        """Two rules with same composite keys -> AmbiguousMatchError."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "wan",
            },
            {
                "uuid": "uuid-2",
                "source_net": "fd00:1::/64",
                "destination_net": "2001:db8:1::/64",
                "interface": "lan",
            },
        ]

        mgr = FwNptManager(mock_client)
        with pytest.raises(AmbiguousMatchError) as exc_info:
            await mgr.ensure(
                state="present",
                params={
                    "source_net": "fd00:1::/64",
                    "destination_net": "2001:db8:1::/64",
                    "interface": "wan",
                },
            )

        assert len(exc_info.value.uuids) == 2
        assert "uuid-1" in exc_info.value.uuids
        assert "uuid-2" in exc_info.value.uuids
        assert exc_info.value.match_keys == {
            "source_net": "fd00:1::/64",
            "destination_net": "2001:db8:1::/64",
        }
