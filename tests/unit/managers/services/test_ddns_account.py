"""Unit tests for opnsense.managers.ddns_account.DdnsAccountManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.services.ddns_account import DdnsAccountManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create_new_account(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
                "service": "cloudflare",
                "username": "user@example.com",
                "password": "api-token",
                "zone": "example.com",
                "enabled": "1",
            },
        )

        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_awaited_once_with("dyndns/service/reconfigure", timeout=30)

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
                "service": "cloudflare",
                "username": "user@example.com",
            },
        ]

        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
                "service": "cloudflare",
                "username": "user@example.com",
            },
        )

        assert result.changed is False
        assert result.action == "noop"

    async def test_update(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {
                "uuid": "uuid-1",
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
                "service": "cloudflare",
                "username": "user@example.com",
                "enabled": "1",
            },
        ]
        mock_client.get.return_value = {
            "account": {
                "uuid": "uuid-1",
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
                "service": "cloudflare",
                "username": "user@example.com",
                "enabled": "1",
            },
        }
        mock_client.update.return_value = {"result": "saved"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(
            state="present",
            params={
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
                "service": "cloudflare",
                "username": "user@example.com",
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
            {
                "uuid": "uuid-1",
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
            },
        ]
        mock_client.get.return_value = {
            "account": {
                "uuid": "uuid-1",
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
            },
        }
        mock_client.delete.return_value = {"result": "deleted"}
        mock_client.reconfigure.return_value = {"status": "ok"}

        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(
            state="absent",
            params={
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
            },
        )

        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []

        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(state="absent", params={"description": "nonexistent"})

        assert result.changed is False


@pytest.mark.asyncio
class TestCheckMode:
    """Tests for check_mode (dry run)."""

    async def test_check_mode_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(
            "present",
            params={
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
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
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
            },
        ]
        mock_client.get.return_value = {
            "account": {
                "uuid": "uuid-1",
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
            },
        }
        mgr = DdnsAccountManager(mock_client)
        result = await mgr.ensure(
            "absent",
            params={
                "description": "Cloudflare DDNS",
                "hostnames": "test.example.com",
                "checkip": "web_cloudflare",
            },
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
            message="invalid", endpoint="dyndns/accounts/addItem"
        )

        mgr = DdnsAccountManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.base"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.ensure(
                state="present",
                params={
                    "description": "bad",
                    "hostnames": "test.example.com",
                    "checkip": "web_cloudflare",
                },
            )

        assert any("create failed" in r.message for r in caplog.records)

    async def test_invalid_state(self, mock_client: AsyncMock) -> None:
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(ValueError, match="Invalid state"):
            await mgr.ensure(state="running", params={"description": "x"})


@pytest.mark.asyncio
class TestFieldValidation:
    """FieldValidationError raised before API call for bad params."""

    async def test_empty_description_raises_before_api_call(self, mock_client: AsyncMock) -> None:
        """Empty required 'description' raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": ""},
            )
        mock_client.create.assert_not_awaited()

    async def test_missing_required_description_raises_before_api_call(
        self, mock_client: AsyncMock
    ) -> None:
        """Missing required 'description' raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", params={"service": "cloudflare"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_enabled_bool_str(self, mock_client: AsyncMock) -> None:
        """Invalid enabled value raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "enabled": "yes",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_wildcard_bool_str(self, mock_client: AsyncMock) -> None:
        """Invalid wildcard value raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "wildcard": "true",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_invalid_force_ssl_bool_str(self, mock_client: AsyncMock) -> None:
        """Invalid force_ssl value raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "force_ssl": "on",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_checkip_timeout_below_min(self, mock_client: AsyncMock) -> None:
        """checkip_timeout below min raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "checkip_timeout": "0",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_ttl_below_min(self, mock_client: AsyncMock) -> None:
        """ttl below min raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={
                    "description": "bad",
                    "ttl": "30",
                },
            )
        mock_client.create.assert_not_awaited()

    async def test_description_exceeds_max_length(self, mock_client: AsyncMock) -> None:
        """Description exceeding max_length raises FieldValidationError."""
        mgr = DdnsAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure(
                "present",
                params={"description": "x" * 256},
            )
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRedactFields:
    """Tests for REDACT_FIELDS on DdnsAccountManager."""

    async def test_redact_fields_defined(self) -> None:
        """DdnsAccountManager has the expected redact fields."""
        assert "password" in DdnsAccountManager.REDACT_FIELDS

    async def test_redact_fields_only_password(self) -> None:
        """Only password is in REDACT_FIELDS."""
        assert {"password"} == DdnsAccountManager.REDACT_FIELDS
