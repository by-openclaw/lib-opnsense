# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.certificates.AcmeCertificateManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseServerError, OpnsenseValidationError
from opnsense.managers.acme.certificates import AcmeCertificateManager


@pytest.mark.asyncio
class TestEnsure:
    async def test_create(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        mock_client.create.return_value = "uuid-new"
        mgr = AcmeCertificateManager(mock_client)
        result = await mgr.ensure(
            "present",
            {
                "name": "fw.example.com",
                "account": "acct-uuid",
                "validationMethod": "val-uuid",
                "keyLength": "key_4096",
            },
        )
        assert result.changed is True
        assert result.action == "created"
        mock_client.reconfigure.assert_not_awaited()

    async def test_noop(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [
            {"uuid": "u1", "name": "fw.example.com", "keyLength": "key_4096"},
        ]
        mgr = AcmeCertificateManager(mock_client)
        result = await mgr.ensure("present", {"name": "fw.example.com", "keyLength": "key_4096"})
        assert result.action == "noop"


@pytest.mark.asyncio
class TestLifecycleVerbs:
    @pytest.mark.parametrize(
        ("method", "verb", "action"),
        [
            ("sign", "sign", "signed"),
            ("revoke", "revoke", "revoked"),
            ("remove_key", "removekey", "key_removed"),
            ("automation", "automation", "automation_run"),
            ("import_", "import", "imported"),
        ],
    )
    async def test_verb_posts_endpoint(
        self, mock_client: AsyncMock, method: str, verb: str, action: str
    ) -> None:
        mock_client.post.return_value = {"status": "OK"}
        mgr = AcmeCertificateManager(mock_client)
        result = await getattr(mgr, method)("u1")
        assert result.changed is True
        assert result.action == action
        assert result.uuid == "u1"
        mock_client.post.assert_awaited_once_with(
            f"acmeclient/certificates/{verb}/u1", timeout=300 if verb == "sign" else None
        )

    async def test_sign_failure_logs_and_reraises(
        self, mock_client: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_client.post.side_effect = OpnsenseValidationError(
            message="sign failed", endpoint="acmeclient/certificates/sign/u1"
        )
        mgr = AcmeCertificateManager(mock_client)
        with (
            caplog.at_level(logging.ERROR, logger="opnsense.managers.acme.certificates"),
            pytest.raises(OpnsenseValidationError),
        ):
            await mgr.sign("u1")
        assert any("sign failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestValidation:
    async def test_missing_name_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeCertificateManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"account": "x"})

    async def test_invalid_keylength_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeCertificateManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"name": "x", "keyLength": "key_1024"})

    async def test_invalid_aliasmode_raises(self, mock_client: AsyncMock) -> None:
        mgr = AcmeCertificateManager(mock_client)
        with pytest.raises(FieldValidationError):
            await mgr.ensure("present", {"name": "x", "aliasmode": "wildcard"})


@pytest.mark.asyncio
class TestIssuedState:
    ROW = {"uuid": "u1", "name": "fw.example.com", "keyLength": "key_4096"}

    async def test_noop_when_issued(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.return_value = {
            "certificate": {**self.ROW, "certRefId": "abc", "statusCode": "200"}
        }
        mgr = AcmeCertificateManager(mock_client)
        r = await mgr.ensure("issued", {"name": "fw.example.com", "keyLength": "key_4096"})
        assert r.changed is False and r.action == "noop"
        mock_client.post.assert_not_awaited()

    def _fast(self, mock_client: AsyncMock) -> AcmeCertificateManager:
        mgr = AcmeCertificateManager(mock_client)
        mgr._issue_poll_interval = 0.0
        mgr._issue_wait_timeout = 1.0
        return mgr

    async def test_signs_when_not_issued_and_waits_for_the_async_issue(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.side_effect = [
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": ""}},
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": "100"}},
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": "100"}},
            {"certificate": {**self.ROW, "certRefId": "abc", "statusCode": "200"}},
        ]
        mock_client.post.return_value = {"status": "OK"}
        r = await self._fast(mock_client).ensure(
            "issued", {"name": "fw.example.com", "keyLength": "key_4096"}
        )
        assert r.changed is True and r.action == "issued" and r.uuid == "u1"
        assert r.after == {"certRefId": "abc", "statusCode": "200"}
        mock_client.post.assert_awaited_once_with("acmeclient/certificates/sign/u1", timeout=300)

    async def test_signs_when_last_status_failed(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.side_effect = [
            {"certificate": {**self.ROW, "certRefId": "abc", "statusCode": "400"}},
            {"certificate": {**self.ROW, "certRefId": "abc", "statusCode": "200"}},
        ]
        mock_client.post.return_value = {"status": "OK"}
        r = await self._fast(mock_client).ensure(
            "issued", {"name": "fw.example.com", "keyLength": "key_4096"}
        )
        assert r.action == "issued"

    async def test_renew_signs_again(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.side_effect = [
            {"certificate": {**self.ROW, "certRefId": "abc", "statusCode": "200"}},
            {"certificate": {**self.ROW, "certRefId": "abc", "statusCode": "200"}},
        ]
        mock_client.post.return_value = {"status": "OK"}
        r = await self._fast(mock_client).ensure(
            "issued", {"name": "fw.example.com", "keyLength": "key_4096"}, renew=True
        )
        assert r.changed is True and r.action == "renewed"

    async def test_in_flight_issue_is_awaited_not_raced(self, mock_client: AsyncMock) -> None:
        """A cron/GUI issue still running (100) → wait; it ends 200 → noop, no second sign."""
        mock_client.search.return_value = [self.ROW]
        mock_client.get.side_effect = [
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": "100"}},
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": "100"}},
            {"certificate": {**self.ROW, "certRefId": "abc", "statusCode": "200"}},
        ]
        r = await self._fast(mock_client).ensure(
            "issued", {"name": "fw.example.com", "keyLength": "key_4096"}
        )
        assert r.changed is False and r.action == "noop"
        mock_client.post.assert_not_awaited()

    async def test_failed_issue_raises(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.side_effect = [
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": ""}},
            {"certificate": {**self.ROW, "certRefId": "", "statusCode": "400"}},
        ]
        mock_client.post.return_value = {"status": "OK"}
        with pytest.raises(OpnsenseServerError) as exc_info:
            await self._fast(mock_client).ensure(
                "issued", {"name": "fw.example.com", "keyLength": "key_4096"}
            )
        assert "statusCode=400" in str(exc_info.value)

    async def test_check_mode_reports_only(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = [self.ROW]
        mock_client.get.return_value = {
            "certificate": {**self.ROW, "certRefId": "", "statusCode": ""}
        }
        r = await AcmeCertificateManager(mock_client).ensure(
            "issued", {"name": "fw.example.com", "keyLength": "key_4096"}, check_mode=True
        )
        assert r.changed is True and r.action == "would_issued"
        mock_client.post.assert_not_awaited()

    async def test_check_mode_object_missing(self, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = []
        r = await AcmeCertificateManager(mock_client).ensure(
            "issued", {"name": "new.example.com"}, check_mode=True
        )
        assert r.changed is True and r.action == "would_issued" and r.uuid is None
        mock_client.create.assert_not_awaited()
        mock_client.post.assert_not_awaited()
