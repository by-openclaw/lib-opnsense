# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.accounts.AcmeAccountManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
from opnsense.managers.acme.accounts import AcmeAccountManager


@pytest.mark.asyncio
class TestEnsurePresent:
    async def test_create_new(self, mock_client: AsyncMock) -> None:
        """ensure present when account missing -> create, no reconfigure."""
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"

        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"name": "letsencrypt-prod", "email": "admin@example.com", "ca": "letsencrypt"},
        )
        assert result.changed is True
        assert result.action == "created"
        assert result.uuid == "uuid-new"
        mock_client.create.assert_awaited_once()
        mock_client.reconfigure.assert_not_awaited()  # _apply_endpoint is None

    async def test_noop_when_matches(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "name": "letsencrypt-prod", "ca": "letsencrypt"},
        ]
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure("present", {"name": "letsencrypt-prod", "ca": "letsencrypt"})
        assert result.changed is False
        assert result.action == "noop"

    async def test_update_on_drift(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "name": "letsencrypt-prod", "ca": "letsencrypt_test"},
        ]
        mock_client.get.return_value = {
            "account": {"uuid": "u1", "name": "letsencrypt-prod", "ca": "letsencrypt_test"},
        }
        mock_client.update.return_value = {"result": "saved"}
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure("present", {"name": "letsencrypt-prod", "ca": "letsencrypt"})
        assert result.changed is True
        assert result.action == "updated"


@pytest.mark.asyncio
class TestEnsureAbsent:
    async def test_delete_existing(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [{"uuid": "u1", "name": "letsencrypt-prod"}]
        mock_client.get.return_value = {"account": {"uuid": "u1", "name": "letsencrypt-prod"}}
        mock_client.delete.return_value = {"result": "deleted"}
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure("absent", {"name": "letsencrypt-prod"})
        assert result.changed is True
        assert result.action == "deleted"

    async def test_noop_when_absent(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure("absent", {"name": "gone"})
        assert result.action == "noop"


@pytest.mark.asyncio
class TestCheckMode:
    async def test_check_mode_create_no_call(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure(
            "present", {"name": "letsencrypt-prod", "ca": "letsencrypt"}, check_mode=True
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.create.assert_not_awaited()


@pytest.mark.asyncio
class TestRegister:
    async def test_register_posts_verb(self, mock_client: AsyncMock) -> None:
        mock_client.post.return_value = {"status": "OK"}
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.register("u1")
        assert result.changed is True
        assert result.action == "registered"
        assert result.uuid == "u1"
        mock_client.post.assert_awaited_once_with("acmeclient/accounts/register/u1")

    async def test_register_failure_logs_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.post.side_effect = OpnsenseValidationError(
            message="register failed", endpoint="acmeclient/accounts/register/u1"
        )
        mgr = AcmeAccountManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.acme.accounts"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.register("u1")
        assert any("register failed" in r.message for r in caplog.records)

    async def test_status_reads_account(self, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = {
            "account": {"statusCode": "200", "statusLastUpdate": "1700000000"},
        }
        mgr = AcmeAccountManager(mock_client)
        st = await mgr.status("u1")
        assert st == {"statusCode": "200", "statusLastUpdate": "1700000000"}


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_name_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"ca": "letsencrypt"})
        mock_client.create.assert_not_awaited()

    async def test_invalid_ca_enum_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeAccountManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"name": "x", "ca": "bogus-ca"})
        mock_client.create.assert_not_awaited()


class TestRedactFields:
    def test_redacts_key_and_eab(self) -> None:
        assert "key" in AcmeAccountManager.REDACT_FIELDS
        assert "eab_hmac" in AcmeAccountManager.REDACT_FIELDS
        assert "eab_kid" in AcmeAccountManager.REDACT_FIELDS

    @pytest.mark.asyncio
    async def test_key_redacted_in_after(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mgr = AcmeAccountManager(mock_client)
        result = await mgr.ensure(
            "present",
            {"name": "letsencrypt-prod", "ca": "letsencrypt", "eab_hmac": "SECRET"},
        )
        assert result.after is not None
        assert result.after["eab_hmac"] == "<REDACTED:eab_hmac>"


@pytest.mark.asyncio
class TestRegisteredState:
    ROW = {"uuid": "u1", "name": "letsencrypt-prod", "ca": "letsencrypt"}

    async def test_noop_when_registered(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.return_value = {"account": {**self.ROW, "statusCode": "200"}}
        r = await AcmeAccountManager(mock_client).ensure(
            "registered", {"name": "letsencrypt-prod", "ca": "letsencrypt"}
        )
        assert r.changed is False and r.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_registers_when_status_missing(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.return_value = {"account": {**self.ROW, "statusCode": ""}}
        mock_client.post.return_value = {"status": "OK"}
        r = await AcmeAccountManager(mock_client).ensure(
            "registered", {"name": "letsencrypt-prod", "ca": "letsencrypt"}
        )
        assert r.changed is True and r.action == "registered" and r.uuid == "u1"
        mock_client.post.assert_awaited_once_with("acmeclient/accounts/register/u1")

    async def test_check_mode(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.return_value = {"account": {**self.ROW, "statusCode": ""}}
        r = await AcmeAccountManager(mock_client).ensure(
            "registered", {"name": "letsencrypt-prod", "ca": "letsencrypt"}, check_mode=True
        )
        assert r.action == "would_register"
        mock_client.post.assert_not_awaited()
