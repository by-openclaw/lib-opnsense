# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Unit tests for opnsense.managers.acme.certificates.AcmeCertificateManager."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from opnsense.exceptions import FieldValidationError, OpnsenseValidationError
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
        mock_client.post.assert_awaited_once_with(f"acmeclient/certificates/{verb}/u1")

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
