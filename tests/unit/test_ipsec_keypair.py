"""Unit tests for opnsense.managers.ipsec_keypair.IpsecKeypairManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.ipsec_keypair import IpsecKeypairManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_keypair(self, mock_client: AsyncMock) -> None:
        """ensure present when key pair does not exist -> create + apply."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "site-a-keypair",
                "keyType": "RSA",
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
                "name": "site-a-keypair",
                "keyType": "RSA",
            },
        ]

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "site-a-keypair",
                "keyType": "RSA",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "name": "site-a-keypair",
                "keyType": "RSA",
            },
        ]
        mock_client.get.return_value = {
            "keyPair": {
                "uuid": "uuid-existing",
                "name": "site-a-keypair",
                "keyType": "RSA",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "name": "site-a-keypair",
                "keyType": "ECDSA",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_keypair(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "name": "site-a-keypair"},
        ]
        mock_client.get.return_value = {
            "keyPair": {"uuid": "uuid-existing", "name": "site-a-keypair"},
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "site-a-keypair"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_awaited_once_with("ipsec/service/reconfigure", timeout=30)

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(state="absent", params={"name": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"name": "site-a-keypair", "keyType": "RSA"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "site-a-keypair"},
        ]
        mock_client.get.return_value = {
            "keyPair": {"uuid": "uuid-1", "name": "site-a-keypair"},
        }

        mgr = IpsecKeypairManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"name": "site-a-keypair"},
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
            message="invalid keypair", endpoint="ipsec/key_pairs/addItem"
        )

        mgr = IpsecKeypairManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"name": "bad"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "name": "site-a-keypair"},
        ]
        mock_client.get.return_value = {
            "keyPair": {"uuid": "uuid-1", "name": "site-a-keypair"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="ipsec/key_pairs/delItem"
        )

        mgr = IpsecKeypairManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"name": "site-a-keypair"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_name_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = IpsecKeypairManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"keyType": "RSA"})
        mock_client.create.assert_not_awaited()

    async def test_name_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = IpsecKeypairManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"name": "x" * 256})
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on IpsecKeypairManager."""

    async def test_redact_fields_defined(self) -> None:
        """IpsecKeypairManager redacts privateKey."""
        assert "privateKey" in IpsecKeypairManager.REDACT_FIELDS
        assert len(IpsecKeypairManager.REDACT_FIELDS) == 1
