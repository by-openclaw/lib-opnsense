"""Unit tests for opnsense.managers.ipsec_child.IpsecChildManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.vpn.ipsec_child import IpsecChildManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_child(self, mock_client: AsyncMock) -> None:
        """ensure present when child SA does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecChildManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "lan-to-lan",
                "connection": "conn-uuid-1",
                "mode": "tunnel",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when child SA matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "lan-to-lan",
                "connection": "conn-uuid-1",
                "mode": "tunnel",
            },
        ]

        mgr = IpsecChildManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "lan-to-lan",
                "connection": "conn-uuid-1",
                "mode": "tunnel",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when mode differs -> update + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "lan-to-lan",
                "mode": "tunnel",
            },
        ]
        mock_client.get.return_value = {
            "child": {
                "uuid": "uuid-existing",
                "description": "lan-to-lan",
                "mode": "tunnel",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecChildManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "lan-to-lan",
                "mode": "transport",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_child(self, mock_client: AsyncMock) -> None:
        """ensure absent when child SA exists -> delete + apply."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "lan-to-lan",
            },
        ]
        mock_client.get.return_value = {
            "child": {
                "uuid": "uuid-existing",
                "description": "lan-to-lan",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecChildManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "lan-to-lan"},
        )

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when child SA does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = IpsecChildManager(mock_client)
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

        mgr = IpsecChildManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "lan-to-lan", "mode": "tunnel"},
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
                "description": "lan-to-lan",
            },
        ]
        mock_client.get.return_value = {
            "child": {
                "uuid": "uuid-1",
                "description": "lan-to-lan",
            },
        }

        mgr = IpsecChildManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "lan-to-lan"},
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
            message="invalid child",
            endpoint="ipsec/connections/addChild",
        )

        mgr = IpsecChildManager(mock_client)
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
                "description": "lan-to-lan",
            },
        ]
        mock_client.get.return_value = {
            "child": {
                "uuid": "uuid-1",
                "description": "lan-to-lan",
            },
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed",
            endpoint="ipsec/connections/delChild",
        )

        mgr = IpsecChildManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="absent",
                params={"description": "lan-to-lan"},
            )

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = IpsecChildManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"mode": "tunnel"})
        mock_client.create.assert_not_awaited()

    async def test_description_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = IpsecChildManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "x" * 256},
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_bool_str_raises(self, mock_client: AsyncMock) -> None:
        mgr = IpsecChildManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "test", "enabled": "yes"},
            )
        mock_client.create.assert_not_awaited()
