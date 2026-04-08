"""Unit tests for opnsense.managers.trust_cert.TrustCertManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.trust_cert import TrustCertManager


@pytest.mark.asyncio
class TestEnsurePresent:
    """Tests for ensure(state='present')."""

    async def test_create_new_cert(self, mock_client: AsyncMock) -> None:
        """ensure present when cert does not exist -> create (no apply)."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Web Server Cert",
                "caref": "ca-uuid",
                "action": "internal",
                "cert_type": "server_cert",
                "lifetime": "397",
                "commonname": "web.example.com",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_not_awaited()

    async def test_noop_when_already_exists_no_drift(self, mock_client: AsyncMock) -> None:
        """ensure present when cert matches -> noop."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "descr": "Web Server Cert",
                "caref": "ca-uuid",
                "cert_type": "server_cert",
            },
        ]

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Web Server Cert",
                "caref": "ca-uuid",
                "cert_type": "server_cert",
            },
        )

        assert result.changed is False
        assert result.action == "noop"
        mock_client.reconfigure.assert_not_awaited()

    async def test_update_when_drift_detected(self, mock_client: AsyncMock) -> None:
        """ensure present when lifetime differs -> update (no apply)."""
        mock_client.search.return_value = [
            {
                "uuid": "uuid-existing",
                "descr": "Web Server Cert",
                "lifetime": "365",
            },
        ]
        mock_client.get.return_value = {
            "cert": {
                "uuid": "uuid-existing",
                "descr": "Web Server Cert",
                "lifetime": "365",
            },
        }
        mock_client.update.return_value = {"result": "saved"}

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Web Server Cert",
                "lifetime": "397",
            },
        )

        assert result.changed is True
        assert result.action == "updated"
        mock_client.reconfigure.assert_not_awaited()


@pytest.mark.asyncio
class TestEnsureAbsent:
    """Tests for ensure(state='absent')."""

    async def test_delete_existing_cert(self, mock_client: AsyncMock) -> None:
        """ensure absent when cert exists -> delete (no apply)."""
        mock_client.search.return_value = [
            {"uuid": "uuid-existing", "descr": "Web Server Cert"},
        ]
        mock_client.get.return_value = {
            "cert": {"uuid": "uuid-existing", "descr": "Web Server Cert"},
        }
        mock_client.delete.return_value = {"result": "deleted"}

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(state="absent", params={"descr": "Web Server Cert"})

        assert result.changed is True
        assert result.action == "deleted"
        mock_client.reconfigure.assert_not_awaited()

    async def test_noop_when_already_absent(self, mock_client: AsyncMock) -> None:
        """ensure absent when cert does not exist -> noop."""
        mock_client.search.return_value = []

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(state="absent", params={"descr": "nonexistent"})

        assert result.changed is False
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={"descr": "Test Cert", "action": "internal"},
            check_mode=True,
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()
        mock_client.reconfigure.assert_not_awaited()

    async def test_check_mode_delete_no_api_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "descr": "Test Cert"},
        ]
        mock_client.get.return_value = {
            "cert": {"uuid": "uuid-1", "descr": "Test Cert"},
        }

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={"descr": "Test Cert"},
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
            message="invalid cert", endpoint="trust/cert/add"
        )

        mgr = TrustCertManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="present", params={"descr": "bad"})

        assert any("create failed" in r.message for r in caplog.records)

    async def test_delete_failure_logs_error_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.search.return_value = [
            {"uuid": "uuid-1", "descr": "Test Cert"},
        ]
        mock_client.get.return_value = {
            "cert": {"uuid": "uuid-1", "descr": "Test Cert"},
        }
        mock_client.delete.side_effect = OpnsenseValidationError(
            message="delete failed", endpoint="trust/cert/del"
        )

        mgr = TrustCertManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(state="absent", params={"descr": "Test Cert"})

        assert any("delete failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_missing_required_descr_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        mgr = TrustCertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"action": "internal"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_action_enum_raises(self, mock_client: AsyncMock) -> None:
        mgr = TrustCertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"descr": "Test Cert", "action": "bogus"},
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_cert_type_enum_raises(self, mock_client: AsyncMock) -> None:
        mgr = TrustCertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"descr": "Test Cert", "cert_type": "ca_cert"},
            )
        mock_client.create.assert_not_awaited()

    async def test_lifetime_below_min_raises(self, mock_client: AsyncMock) -> None:
        mgr = TrustCertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"descr": "Test Cert", "lifetime": "0"},
            )
        mock_client.create.assert_not_awaited()

    async def test_descr_exceeds_max_length_raises(self, mock_client: AsyncMock) -> None:
        mgr = TrustCertManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"descr": "x" * 256},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on TrustCertManager."""

    async def test_redact_fields_defined(self) -> None:
        """TrustCertManager redacts prv, prv_payload, and csr_payload."""
        assert "prv" in TrustCertManager.REDACT_FIELDS
        assert "prv_payload" in TrustCertManager.REDACT_FIELDS
        assert "csr_payload" in TrustCertManager.REDACT_FIELDS
        assert len(TrustCertManager.REDACT_FIELDS) == 3

    async def test_create_redacts_prv_payload_in_result(self, mock_client: AsyncMock) -> None:
        """ensure present create -> prv_payload is redacted in after dict."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = TrustCertManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "descr": "Import Cert",
                "action": "existing",
                "prv_payload": "SECRET-KEY",
                "csr_payload": "SECRET-CSR",
            },
        )

        assert result.changed is True
        assert result.after is not None
        assert result.after["prv_payload"] == "<REDACTED:prv_payload>"
        assert result.after["csr_payload"] == "<REDACTED:csr_payload>"
