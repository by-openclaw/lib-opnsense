"""Unit tests for opnsense.managers.ipsec_psk.IpsecPskManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.vpn.ipsec_psk import IpsecPskManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_psk(self, mock_client: AsyncMock) -> None:
        """ensure present when PSK does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "site-a-psk",
                "ident": "site-a.example.com",
                "Key": "supersecret",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "site-a-psk",
                "ident": "site-a.example.com",
                "Key": "supersecret",
            },
        ]

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "site-a-psk",
                "ident": "site-a.example.com",
                "Key": "supersecret",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "description": "site-a-psk",
                "ident": "site-a.example.com",
            },
        ]
        mock_client.get.return_value = {
            "preSharedKey": {
                "uuid": "uuid-existing",
                "description": "site-a-psk",
                "ident": "site-a.example.com",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "site-a-psk",
                "ident": "site-b.example.com",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_psk(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "description": "site-a-psk"},
        ]
        mock_client.get.return_value = {
            "preSharedKey": {"uuid": "uuid-existing", "description": "site-a-psk"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "site-a-psk"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"description": "site-a-psk", "Key": "secret"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "description": "site-a-psk"},
        ]
        mock_client.get.return_value = {
            "preSharedKey": {"uuid": "uuid-1", "description": "site-a-psk"},
        }

        mgr = IpsecPskManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"description": "site-a-psk"},
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
            message="invalid psk", endpoint="ipsec/pre_shared_keys/addItem"
        )

        mgr = IpsecPskManager(mock_client)
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
            {"uuid": "uuid-1", "description": "site-a-psk"},
        ]
        mock_client.get.return_value = {
            "preSharedKey": {"uuid": "uuid-1", "description": "site-a-psk"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="ipsec/pre_shared_keys/delItem"
        )

        mgr = IpsecPskManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"description": "site-a-psk"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = IpsecPskManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"Key": "secret"})
        mock_client.create.assert_not_awaited()

    async def test_description_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = IpsecPskManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"description": "x" * 256})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on IpsecPskManager."""

    async def test_redact_fields_defined(self) -> None:
        """IpsecPskManager redacts Key."""
        assert "Key" in IpsecPskManager.REDACT_FIELDS
        assert len(IpsecPskManager.REDACT_FIELDS) == 1
